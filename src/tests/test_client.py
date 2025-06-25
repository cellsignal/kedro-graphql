import pytest
from kedro_graphql.models import PipelineInput, Pipeline, TagInput
import json
from celery.states import ALL_STATES
from kedro_graphql.schema import encode_cursor
import pytest_asyncio


@pytest_asyncio.fixture
async def mock_create_pipeline(mock_client, mock_text_in, mock_text_out):

    input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
    output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}

    pipeline_input = PipelineInput(**{
        "name": "example00",
        "state": "READY",
        "data_catalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                         {"name": "text_out", "config": json.dumps(output_dict)}],
        "parameters": [{"name": "example", "value": "hello"},
                       {"name": "duration", "value": "0", "type": "FLOAT"}],
        "tags": [{"key": "author", "value": "opensean"},
                 {"key": "package", "value": "kedro-graphql"}]
    })
    expected = Pipeline.decode(pipeline_input)
    pipeline = await mock_client.create_pipeline(pipeline_input)
    return pipeline_input, expected, pipeline


@pytest_asyncio.fixture
async def mock_create_pipeline_staged(mock_client, mock_text_in, mock_text_out):

    input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
    output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}

    pipeline_input = PipelineInput(**{
        "name": "example00",
        "state": "STAGED",
        "data_catalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                         {"name": "text_out", "config": json.dumps(output_dict)}],
        "parameters": [{"name": "example", "value": "hello"},
                       {"name": "duration", "value": "0", "type": "FLOAT"}],
        "tags": [{"key": "author", "value": "opensean"},
                 {"key": "package", "value": "kedro-graphql"}]
    })

    expected = Pipeline.decode(pipeline_input)
    pipeline = await mock_client.create_pipeline(pipeline_input)
    return pipeline_input, expected, pipeline


@pytest_asyncio.fixture
async def mock_create_pipeline_staged_unique(mock_client, mock_text_in, mock_text_out):

    input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
    output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}

    pipeline_input = PipelineInput(**{
        "name": "example00",
        "state": "STAGED",
        "data_catalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                         {"name": "text_out", "config": json.dumps(output_dict)}],
        "parameters": [{"name": "example", "value": "hello"},
                       {"name": "duration", "value": "0", "type": "FLOAT"}],
        "tags": [{"key": "author", "value": "opensean"},
                 {"key": "package", "value": "kedro-graphql"},
                 {"key": "unique", "value": "unique"}]
    })

    expected = Pipeline.decode(pipeline_input)
    pipeline = await mock_client.create_pipeline(pipeline_input)
    return pipeline_input, expected, pipeline


class TestKedroGraphqlClient:

    @pytest.mark.asyncio
    async def test_create_pipeline(self, mock_create_pipeline_staged):

        pipeline_input, expected, pipeline = mock_create_pipeline_staged

        assert pipeline.name == expected.name
        assert pipeline.data_catalog == expected.data_catalog
        assert pipeline.parameters == expected.parameters
        assert pipeline.tags == expected.tags

    @pytest.mark.asyncio
    async def test_read_pipeline(self, mock_create_pipeline_staged, mock_client):

        pipeline_input, expected, pipeline = mock_create_pipeline_staged
        r = await mock_client.read_pipeline(id=pipeline.id)
        assert r.name == expected.name
        assert r.data_catalog == expected.data_catalog
        assert r.parameters == expected.parameters
        assert r.tags == expected.tags

    @pytest.mark.asyncio
    async def test_read_pipelines(self, mock_create_pipeline_staged_unique, mock_client):

        pipeline_input, expected, pipeline = mock_create_pipeline_staged_unique
        limit = 1
        filter = "{\"tags.key\": \"unique\", \"tags.value\": \"unique\"}"
        cursor = encode_cursor(pipeline.id)
        sort = "[(\"created_at\", -1)]"
        r = await mock_client.read_pipelines(filter=filter, limit=limit, cursor=cursor, sort=sort)
        assert r.pipelines[0].name == expected.name
        assert r.pipelines[0].data_catalog == expected.data_catalog
        assert r.pipelines[0].parameters == expected.parameters
        assert r.pipelines[0].tags == expected.tags

    @pytest.mark.asyncio
    async def test_update_pipeline(self, mock_create_pipeline_staged, mock_client):

        pipeline_input, expected, pipeline = mock_create_pipeline_staged
        pipeline_input.tags.append(TagInput(key="test-update", value="updated"))
        r = await mock_client.update_pipeline(id=pipeline.id, pipeline_input=pipeline_input)
        assert r.tags[-1].key == "test-update"
        assert r.tags[-1].value == "updated"

    @pytest.mark.asyncio
    async def test_delete_pipeline(self, mock_create_pipeline_staged, mock_client):

        pipeline_input, expected, pipeline = mock_create_pipeline_staged
        r = await mock_client.delete_pipeline(id=pipeline.id)
        assert r.id == pipeline.id

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_events(self, mock_create_pipeline, mock_client):

        pipeline_input, expected, pipeline = mock_create_pipeline

        async for result in mock_client.pipeline_events(id=pipeline.id):
            assert result.status in ALL_STATES

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_logs(self, mock_create_pipeline, mock_client):

        pipeline_input, expected, pipeline = mock_create_pipeline

        async for result in mock_client.pipeline_logs(id=pipeline.id):
            assert result.id == pipeline.id
