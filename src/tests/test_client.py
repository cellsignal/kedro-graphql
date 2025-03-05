import pytest
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import PipelineInput, Pipeline, TagInput
from multiprocessing import Process
import uvicorn
import time
import json
from pathlib import Path
from kedro_graphql.asgi import KedroGraphQL
from celery.states import ALL_STATES
from kedro_graphql.schema import encode_cursor
import multiprocessing as mp
import tempfile


if mp.get_start_method(allow_none=True) != "spawn":
    mp.set_start_method("spawn")


def start_server():

    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory() as tmp2:
            bootstrap_project(Path.cwd())
            session = KedroSession.create()
            app = KedroGraphQL(kedro_session=session)
            app.config["KEDRO_GRAPHQL_LOG_PATH_PREFIX"] = tmp
            app.config["KEDRO_GRAPHQL_LOG_TMP_DIR"] = tmp2
            uvicorn.run(app,
                        host="localhost",
                        port=5000)


@pytest.fixture(scope="session")
def setup():
    proc = Process(target=start_server, args=())
    proc.start()
    time.sleep(2)
    yield
    proc.terminate()


@pytest.fixture
def mock_client(setup):
    return KedroGraphqlClient(uri="http://localhost:5000/graphql",
                              ws="ws://localhost:5000/graphql")


@pytest.fixture
@pytest.mark.asyncio
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


@pytest.fixture
@pytest.mark.asyncio
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


@pytest.fixture
@pytest.mark.asyncio
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

        pipeline_input, expected, pipeline = await mock_create_pipeline_staged

        assert pipeline.name == expected.name
        assert pipeline.data_catalog == expected.data_catalog
        assert pipeline.parameters == expected.parameters
        assert pipeline.tags == expected.tags

    @pytest.mark.asyncio
    async def test_read_pipeline(self, mock_create_pipeline_staged, mock_client):

        pipeline_input, expected, pipeline = await mock_create_pipeline_staged
        r = await mock_client.read_pipeline(id=pipeline.id)
        assert r.name == expected.name
        assert r.data_catalog == expected.data_catalog
        assert r.parameters == expected.parameters
        assert r.tags == expected.tags

    @pytest.mark.asyncio
    async def test_read_pipelines(self, mock_create_pipeline_staged_unique, mock_client):

        pipeline_input, expected, pipeline = await mock_create_pipeline_staged_unique
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

        pipeline_input, expected, pipeline = await mock_create_pipeline_staged
        pipeline_input.tags.append(TagInput(key="test-update", value="updated"))
        r = await mock_client.update_pipeline(id=pipeline.id, pipeline_input=pipeline_input)
        assert r.tags[-1].key == "test-update"
        assert r.tags[-1].value == "updated"

    @pytest.mark.asyncio
    async def test_delete_pipeline(self, mock_create_pipeline_staged, mock_client):

        pipeline_input, expected, pipeline = await mock_create_pipeline_staged
        r = await mock_client.delete_pipeline(id=pipeline.id)
        assert r.id == pipeline.id

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_events(self, mock_create_pipeline, mock_client):

        pipeline_input, expected, pipeline = await mock_create_pipeline

        async for result in mock_client.pipeline_events(id=pipeline.id):
            assert result.status in ALL_STATES

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_logs(self, mock_create_pipeline, mock_client):

        pipeline_input, expected, pipeline = await mock_create_pipeline

        async for result in mock_client.pipeline_logs(id=pipeline.id):
            assert result.id == pipeline.id
