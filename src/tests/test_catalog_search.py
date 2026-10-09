import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, MagicMock

import pytest
from bson import ObjectId
from kedro_graphql.config import KedroGraphQLConfig, load_config
from kedro_graphql.catalog_search import (
    CatalogSearchInput, build_dataset_search, build_pipeline_document, search_catalog,
    mask_dataset, pipeline_document_update, public_pipeline_document, search_entry,
)
from kedro_graphql.dataset_search_maintenance import maintain_dataset_search
from kedro_graphql.models import Pipeline, State
from kedro_graphql.backends.mongodb import MongoBackend


def dataset(name='FULL.bam', **config):
    return {'name': name, 'config': json.dumps({'type': 'bioseq.BamDataset', **config}), 'tags': []}


def document(index, *, tags=(), catalog=(), enriched=True):
    value = {'_id': ObjectId(f'{index:024x}'), 'name': 'analysis', 'tags': list(tags),
             'data_catalog': list(catalog), 'created_at': datetime(2026, 1, index, tzinfo=timezone.utc)}
    if enriched:
        value['dataset_search'] = build_dataset_search(value['data_catalog'], value['tags'])
    return value


class Cursor:
    def __init__(self, documents):
        self.documents = documents
        self.closed = False
    def __aiter__(self):
        async def iterate():
            for value in self.documents:
                yield value
        return iterate()
    def max_time_ms(self, timeout):
        return self
    async def close(self):
        self.closed = True


def services_for_search(documents, config=None):
    def find(query, projection=None):
        version = query['$and'][1].get('dataset_search.version')
        values = documents
        if version == 2:
            values = [value for value in documents if value.get('dataset_search', {}).get('version') == 2]
        elif isinstance(version, dict):
            values = [value for value in documents if value.get('dataset_search', {}).get('version') != 2]
        return Cursor(values)
    collection = Mock(find=Mock(side_effect=find))
    return SimpleNamespace(config=config or KedroGraphQLConfig(), backend=SimpleNamespace(_get_collection=lambda: collection)), collection


def test_projection_and_atomic_best_effort():
    catalog = [dataset(filepath='s3://BUCKET/FULL.bam', paths=['/Other', None])]
    projection = build_dataset_search(catalog, [{'key': 'barcode', 'value': 'L12345'}])
    assert projection['version'] == 2
    assert projection['pipeline_tags'] == [{'key': 'barcode', 'value_folded': 'l12345'}]
    assert projection['datasets'][0]['locations_folded'] == ['/other', 's3://bucket/full.bam']
    raw = {'data_catalog': catalog, 'tags': [{'key': 'barcode', 'value': 'L12345'}]}
    pipeline = Mock(to_dict=Mock(return_value=raw), id='id')
    assert build_pipeline_document(pipeline)['dataset_search'] == projection
    assert public_pipeline_document(raw) == {'data_catalog': catalog, 'tags': raw['tags']}
    pipeline.to_dict.return_value = {'data_catalog': [{'name': 'bad', 'config': '{'}]}
    assert pipeline_document_update(build_pipeline_document(pipeline))['$unset'] == {'dataset_search': ''}


@pytest.mark.asyncio
@pytest.mark.parametrize('enriched', [True, False])
async def test_union_parent_tags_locations_and_type_only_dataset(enriched):
    docs = [document(1, tags=[{'key': 'barcode', 'value': 'L12345'}], catalog=[dataset('memory'), dataset('other', type='CSV')], enriched=enriched),
            document(2, catalog=[dataset('logical12345'), dataset('file', filepath='s3://bucket/L12345/run.bam')], enriched=enriched),
            document(3, catalog=[dataset('logical12345')], enriched=enriched)]
    services, collection = services_for_search(docs)
    result = await search_catalog(services, CatalogSearchInput(text='12345', dataset_type='BamDataset'))
    assert [row.id for row in result.pipelines.pipelines] == [str(docs[1]['_id']), str(docs[0]['_id'])]
    assert [row.dataset.name for row in result.datasets.datasets] == ['file', 'memory']
    assert 'name_folded' not in str(collection.find.call_args)


@pytest.mark.asyncio
async def test_independent_connections_and_literal_matches():
    services, _ = services_for_search([document(1, catalog=[dataset('x', filepath='/literal/a.*b')])])
    result = await search_catalog(services, CatalogSearchInput(text='a.*'), connection='pipelines')
    assert len(result.pipelines.pipelines) == 1 and not result.datasets.datasets
    result = await search_catalog(services, CatalogSearchInput(text='a.*'), connection='datasets')
    assert not result.pipelines.pipelines and len(result.datasets.datasets) == 1
    result = await search_catalog(services, CatalogSearchInput(text='axb'))
    assert not result.pipelines.pipelines and not result.datasets.datasets


@pytest.mark.asyncio
async def test_exact_id_empty_text_tags_policy_and_masks():
    config = KedroGraphQLConfig(catalog_search_tag_keys=['barcode'], pipeline_name_disallowlist=['private'],
                              dataset_filepath_masks=[{'prefix': '/secret/', 'mask': '/public/'}])
    doc = document(1, tags=[{'key': 'other', 'value': '12345'}], catalog=[dataset(filepath='/secret/file')])
    services, collection = services_for_search([doc], config)
    result = await search_catalog(services, CatalogSearchInput(text='12345'))
    assert not result.pipelines.pipelines
    result = await search_catalog(services, CatalogSearchInput(pipeline_id=str(doc['_id'])))
    assert json.loads(result.datasets.datasets[0].dataset.config)['filepath'] == '/public/file'
    assert json.loads(result.pipelines.pipelines[0].data_catalog[0].config)['filepath'] == '/public/file'
    assert 'private' in str(collection.find.call_args)
    assert ObjectId(str(doc['_id'])) in collection.find.call_args.args[0]['$and'][0]['$and'][1].values()


@pytest.mark.asyncio
async def test_cursor_pages_dedup_and_query_binding():
    docs = [document(i, tags=[{'key': 'barcode', 'value': '123'}], catalog=[dataset('same'), dataset('same')]) for i in range(1, 4)]
    services, _ = services_for_search(docs)
    search = CatalogSearchInput(text='123')
    first = await search_catalog(services, search, pipeline_limit=1, dataset_limit=2)
    second = await search_catalog(services, search, pipeline_limit=1, dataset_limit=2,
                                  pipeline_cursor=first.pipelines.page_meta.next_cursor,
                                  dataset_cursor=first.datasets.page_meta.next_cursor)
    assert first.pipelines.pipelines[0].id == str(docs[2]['_id'])
    assert second.pipelines.pipelines[0].id == str(docs[1]['_id'])
    assert [row.catalog_index for row in first.datasets.datasets] == [0, 1]
    assert first.datasets.datasets[0].pipeline_id != second.datasets.datasets[0].pipeline_id
    with pytest.raises(ValueError, match='cursor'):
        await search_catalog(services, CatalogSearchInput(text='456'), dataset_cursor=first.datasets.page_meta.next_cursor)
    with pytest.raises(ValueError, match='cursor'):
        await search_catalog(services, search, pipeline_cursor=first.datasets.page_meta.next_cursor)


@pytest.mark.asyncio
async def test_validation_and_timeout():
    services, collection = services_for_search([], KedroGraphQLConfig(dataset_search_timeout_seconds=.001))
    for search in [CatalogSearchInput(text='ab'), CatalogSearchInput(text='x'*1025), CatalogSearchInput(pipeline_id='invalid')]:
        with pytest.raises(ValueError):
            await search_catalog(services, search)
    with pytest.raises(ValueError):
        await search_catalog(services, CatalogSearchInput(text='abc'), pipeline_limit=201)
    class SlowCursor(Cursor):
        def __aiter__(self):
            async def iterate():
                await asyncio.sleep(.02)
                yield {}
            return iterate()
    collection.find.side_effect = None
    collection.find.return_value = SlowCursor([])
    with pytest.raises(ValueError, match='timed out'):
        await search_catalog(services, CatalogSearchInput(text='abc'))


def test_masks_preserve_original():
    raw = dataset(filepath='/secret/f', path='/secret/p', paths=['/secret/a', '/other'])
    config = json.loads(mask_dataset(raw, [{'prefix': '/secret/', 'mask': '/visible/'}])['config'])
    assert config['filepath'] == '/visible/f' and config['path'] == '/visible/p'
    assert config['paths'] == ['/visible/a', '/other'] and '/secret/f' in raw['config']


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['create', 'update', 'update_if_current'])
@pytest.mark.parametrize('broken', [False, True])
async def test_all_mongo_writers_use_atomic_projection(method, broken):
    identity = '000000000000000000000001'
    catalog = [dataset() if not broken else {'name': 'bad', 'config': '{', 'tags': []}]
    pipeline = Pipeline.from_dict({'id': identity, 'name': 'analysis', 'data_catalog': catalog})
    collection = Mock(insert_one=AsyncMock(return_value=SimpleNamespace(inserted_id=ObjectId(identity))),
                      find_one=AsyncMock(return_value={'_id': ObjectId(identity), 'name': 'analysis', 'data_catalog': catalog}),
                      update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)))
    backend = MongoBackend()
    backend._get_collection = Mock(return_value=collection)
    backend.read = AsyncMock(return_value=pipeline)
    if method == 'create':
        await backend.create(pipeline)
        payload = collection.insert_one.call_args.args[0]
        assert ('dataset_search' in payload) is not broken
    else:
        if method == 'update':
            await backend.update(pipeline)
        else:
            await backend.update_if_current(pipeline, State.STARTED, 1)
        query, payload = collection.update_one.call_args.args
        assert ('$unset' in payload) is broken
        assert ('dataset_search' in payload['$set']) is not broken
        if method == 'update_if_current':
            assert query['status'] == {'$size': 1}
        collection.update_one.return_value.matched_count = 0
        if method == 'update_if_current':
            assert await backend.update_if_current(pipeline, State.STARTED, 1) is None


def test_maintenance_check_and_race_retry():
    original = {'_id': ObjectId(), 'data_catalog': [dataset('before')]}
    changed = {**original, 'data_catalog': [dataset('after')]}
    collection = Mock(find=Mock(return_value=[original]), update_one=Mock(side_effect=[SimpleNamespace(matched_count=0), SimpleNamespace(matched_count=1)]),
                      find_one=Mock(return_value=changed))
    counts = maintain_dataset_search(collection)
    assert counts['missing'] == 1
    collection.update_one.assert_not_called()
    counts = maintain_dataset_search(collection, True)
    assert counts['repaired'] == 1
    query, update = collection.update_one.call_args.args
    assert query['data_catalog'] == changed['data_catalog']
    assert update['$set']['dataset_search'] == build_dataset_search(changed['data_catalog'])
    assert 'data_catalog' not in update['$set']


def test_search_timeout_config():
    assert load_config({'dataset_search_timeout_seconds': 2}).dataset_search_timeout_seconds == 2
    for value in (0, float('inf'), float('nan')):
        with pytest.raises(ValueError):
            load_config({'dataset_search_timeout_seconds': value})


def test_maintenance_reports_unsupported_inconsistent_and_unrepairable():
    catalog = [dataset()]
    records = [
        {'_id': ObjectId(), 'data_catalog': catalog, 'dataset_search': {'version': 1}},
        {'_id': ObjectId(), 'data_catalog': catalog, 'dataset_search': {'version': 2, 'datasets': []}},
        {'_id': ObjectId(), 'data_catalog': catalog, 'dataset_search': build_dataset_search(catalog)},
        {'_id': ObjectId(), 'data_catalog': [{'name': 'bad', 'config': '{'}]},
    ]
    collection = Mock(find=Mock(return_value=records))
    counts = maintain_dataset_search(collection)
    assert counts['unsupported'] == counts['inconsistent'] == counts['consistent'] == counts['failed'] == 1
    collection.update_one.assert_not_called()
    racing = Mock(find=Mock(return_value=[records[0]]), update_one=Mock(return_value=SimpleNamespace(matched_count=0)),
                  find_one=Mock(return_value=records[0]))
    assert maintain_dataset_search(racing, True)['failed'] == 1
    assert racing.update_one.call_count == 3


def test_maintenance_commands_are_registered_and_do_not_expose_connection_uri():
    from unittest.mock import patch
    from click.testing import CliRunner
    from kedro_graphql.commands import gql
    from pymongo.errors import ConnectionFailure
    client = MagicMock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    collection = client.__getitem__.return_value.__getitem__.return_value
    collection.find.return_value = []
    config = KedroGraphQLConfig(mongo_uri='mongodb://username:password@private-host/db')
    with patch('kedro_graphql.commands.load_config', return_value=config), patch('pymongo.MongoClient', return_value=client):
        result = CliRunner().invoke(gql, ['--project-version', 'test', 'dataset-search', 'check'], obj=SimpleNamespace(package_name='kedro_graphql'))
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)['checked'] == 0
        collection.update_one.assert_not_called()
        collection.find.side_effect = ConnectionFailure(config.mongo_uri)
        result = CliRunner().invoke(gql, ['--project-version', 'test', 'dataset-search', 'rebuild'], obj=SimpleNamespace(package_name='kedro_graphql'))
        assert result.exit_code == 1
        assert 'password' not in result.output


@pytest.mark.asyncio
async def test_mixed_iso_and_bson_dates_sort_in_utc():
    early = document(1, tags=[{'key': 'x', 'value': '123'}])
    late = document(2, tags=[{'key': 'x', 'value': '123'}])
    late['created_at'] = '2026-01-02T01:00:00+02:00'
    services, _ = services_for_search([early, late])
    result = await search_catalog(services, CatalogSearchInput(text='123'))
    assert [row.id for row in result.pipelines.pipelines] == [str(late['_id']), str(early['_id'])]


def test_term_expansion_and_config_lists():
    from unittest.mock import patch
    from kedro_graphql.catalog_search import expanded_terms
    config = load_config({'catalog_search_tag_keys': '["barcode"]', 'catalog_search_term_expander': 'example.expand'})
    assert config.catalog_search_tag_keys == ['barcode']
    with patch('kedro_graphql.catalog_search.importlib.import_module', return_value=SimpleNamespace(expand=lambda text: ['L123', '123'])):
        assert expanded_terms('l123', config) == ['123', 'l123']
    with patch('kedro_graphql.catalog_search.importlib.import_module', return_value=SimpleNamespace(expand=lambda text: 'bad')):
        with pytest.raises(ValueError, match='list of strings'):
            expanded_terms('123', config)


def test_rebuild_compares_tag_changes_and_presence():
    original = document(1, tags=[{'key': 'barcode', 'value': 'before'}], enriched=False)
    changed = {**original, 'tags': [{'key': 'barcode', 'value': 'after'}]}
    collection = Mock(find=Mock(return_value=[original]),
                      update_one=Mock(side_effect=[SimpleNamespace(matched_count=0), SimpleNamespace(matched_count=1)]),
                      find_one=Mock(return_value=changed))
    assert maintain_dataset_search(collection, True)['repaired'] == 1
    first, second = collection.update_one.call_args_list
    assert first.args[0]['tags'] == original['tags']
    assert second.args[0]['tags'] == changed['tags']
    assert second.args[1]['$set']['dataset_search'] == build_dataset_search(changed['data_catalog'], changed['tags'])
    absent = {'_id': ObjectId()}
    collection = Mock(find=Mock(return_value=[absent]), update_one=Mock(return_value=SimpleNamespace(matched_count=1)))
    maintain_dataset_search(collection, True)
    assert collection.update_one.call_args.args[0]['tags'] == {'$exists': False}


@pytest.mark.asyncio
async def test_candidate_projection_and_changed_source_rejected():
    doc = document(1, tags=[{'key': 'barcode', 'value': '123'}], catalog=[dataset()])
    services, collection = services_for_search([doc])
    await search_catalog(services, CatalogSearchInput(text='123'))
    assert 'data_catalog' not in collection.find.call_args_list[0].args[1]
    candidate = {key: value for key, value in doc.items() if key != 'data_catalog'}
    changed = {**doc, 'tags': []}
    collection.find.side_effect = [Cursor([candidate]), Cursor([]), Cursor([changed])]
    with pytest.raises(ValueError, match='changed during search'):
        await search_catalog(services, CatalogSearchInput(text='123'))


def test_schema_replaces_search_modes_with_independent_connections():
    import strawberry
    from kedro_graphql.schema import Query
    schema = strawberry.Schema(query=Query).as_str()
    assert 'searchCatalogPipelines' in schema and 'searchCatalogDatasets' in schema
    assert 'searchDatasets(' not in schema and 'DatasetMatchMode' not in schema
