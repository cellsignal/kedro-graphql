import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import tempfile

import pytest
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

from kedro_graphql.asgi import KedroGraphQL
from kedro_graphql.models import (
    DataSet,
    Parameter,
    Pipeline,
    PipelineStatus,
    State,
    Tag,
)
from kedro_graphql.tasks import run_pipeline
from fastapi.middleware.cors import CORSMiddleware
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.config import config as CONFIG
from multiprocessing import Process
import uvicorn
from pathlib import Path
from kedro_graphql.asgi import KedroGraphQL
import multiprocessing as mp
import tempfile
import pytest_asyncio

# enable events endpoint
CONFIG["KEDRO_GRAPHQL_EVENTS_CONFIG"] = {"event00": {
    "source": "example.com", "type": "com.example.event"}}

# use "test_pipelines" as the collection name for testing
CONFIG["KEDRO_GRAPHQL_MONGO_DB_COLLECTION"] = "test_pipelines"
CONFIG["MONGO_DB_NAME"] = "test_pipelines"


if mp.get_start_method(allow_none=True) != "spawn":
    mp.set_start_method("spawn")


@pytest.fixture(scope="session")
def kedro_session():
    bootstrap_project(Path.cwd())
    return KedroSession.create()


def start_server():

    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory() as tmp2:
            bootstrap_project(Path.cwd())
            session = KedroSession.create()
            app = KedroGraphQL(kedro_session=session, config=CONFIG)
            app.config["KEDRO_GRAPHQL_LOG_PATH_PREFIX"] = tmp
            app.config["KEDRO_GRAPHQL_LOG_TMP_DIR"] = tmp2
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            uvicorn.run(app,
                        host="localhost",
                        port=5000)


@pytest.fixture(scope="session")
def mock_server():
    proc = Process(target=start_server, args=())
    proc.start()
    yield
    proc.terminate()


@pytest_asyncio.fixture
async def mock_client(mock_server):
    client = KedroGraphqlClient(uri_graphql="http://localhost:5000/graphql",
                                uri_ws="ws://localhost:5000/graphql")
    yield client
    await client.close_sessions()


@pytest.fixture(scope="session")
def mock_app(kedro_session):

    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory() as tmp2:
            app = KedroGraphQL(kedro_session=kedro_session)
            app.config["KEDRO_GRAPHQL_LOG_PATH_PREFIX"] = tmp
            app.config["KEDRO_GRAPHQL_LOG_TMP_DIR"] = tmp2
            yield app


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://',
        'result_backend': 'redis://',
        'result_extened': True,
        'worker_send_task_events': True,
        'task_send_sent_event': True,
        'task_store_eager_result': True,
        'task_always_eager': False,
        'task_ignore_result': False,
        'imports': ["kedro_graphql.tasks"]

    }


@pytest.fixture(scope='session')
def mock_celery_session_app(mock_app, celery_session_app):
    celery_session_app.kedro_graphql_backend = mock_app.backend
    celery_session_app.kedro_graphql_schema = mock_app.schema
    return celery_session_app


@pytest.fixture(scope="session")
def celery_worker_parameters():
    return {"without_heartbeat": False}


@pytest.fixture
def mock_info_context(mock_app):

    class Request():
        app = mock_app

    with patch("strawberry.types.Info.context", {"request": Request()}) as m:
        yield m


# refer to https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html for info on tmp_path fixture
@pytest.fixture
def mock_text_in(tmp_path):
    text_in = tmp_path / "text_in.txt"
    text_in.write_text("hello")
    return text_in


@pytest.fixture
def mock_text_out(tmp_path):
    text_out = tmp_path / "text_out.txt"
    text_out.write_text("good bye")
    return text_out


@pytest.fixture
def mock_text_in_tsv(tmp_path):
    text = tmp_path / "text_in.tsv"
    text.write_text(
        "Some parameter\tOther parameter\tLast parameter\nCONST\t123456\t12.45")
    return text


@pytest.fixture
def mock_text_out_tsv(tmp_path):
    text = tmp_path / "text_out.tsv"
    text.write_text(
        "Some parameter\tOther parameter\tLast parameter\nCONST\t123456\t12.45")
    return text


@pytest.fixture
def mock_uppercased_txt(tmp_path):
    text = tmp_path / "uppercased.txt"
    text.write_text("HELLO")
    return text


@pytest.fixture
def mock_reversed_txt(tmp_path):
    text = tmp_path / "reversed.txt"
    text.write_text("OLLEH")
    return text


@pytest.fixture
def mock_timestamped_txt(tmp_path):
    text = tmp_path / "timestamped.txt"
    # Don't write to this file. We need an missing file to test the run "only_missing" mutation
    return text


@pytest.fixture
def mock_pipeline(mock_celery_session_app,
                  celery_session_worker,
                  depends_on_current_app,
                  mock_app,
                  tmp_path,
                  mock_text_in,
                  mock_text_out):

    inputs = [{"name": "text_in", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name": "text_out", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_out)})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "opensean"}, {
        "key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example00",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter(**p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.READY,
                               runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                               session=mock_app.kedro_session.session_id,
                               started_at=datetime.now(),
                               task_name=str(run_pipeline))]
    )

    p.created_at = datetime.now()
    p = mock_app.backend.create(p)

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs={"id": str(p.id),
                                              "name": "example00",
                                              "data_catalog": serial["data_catalog"],
                                              "parameters": serial["parameters"],
                                              "runner": mock_app.config["KEDRO_GRAPHQL_RUNNER"]},
                                      countdown=0.1)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p.status[-1].task_id = result.id
    p = mock_app.backend.update(p)
    return p


@pytest.fixture
def mock_pipeline2(mock_app, tmp_path, mock_text_in, mock_text_out):

    inputs = [{"name": "text_in", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name": "text_out", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_out)})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "opensean"}, {
        "key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example00",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter(**p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.READY,
                               runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                               session=mock_app.kedro_session.session_id,
                               started_at=datetime.now(),
                               task_name=str(run_pipeline))]
    )

    p.created_at = datetime.now()
    p = mock_app.backend.create(p)

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs={"id": str(p.id),
                                              "name": "example00",
                                              "data_catalog": serial["data_catalog"],
                                              "parameters": serial["parameters"],
                                              "runner": mock_app.config["KEDRO_GRAPHQL_RUNNER"]},
                                      countdown=0.1)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p.status[-1].task_id = result.id
    p = mock_app.backend.update(p)
    return p


@pytest.fixture
def mock_pipeline_no_task(mock_app, mock_text_in, mock_text_out):

    inputs = [{"name": "text_in", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name": "text_out", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_out)})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "opensean"}, {
        "key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example00",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter(**p) for p in parameters],
        tags=[Tag(**p) for p in tags]
    )

    p.status.append(PipelineStatus(state=State.READY,
                                   runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                                   session=mock_app.kedro_session.session_id,
                                   started_at=datetime.now(),
                                   task_name=str(run_pipeline)))

    p.created_at = datetime.now()
    return p


@pytest.fixture(autouse=True)
def delete_pipeline_collection(mock_app):
    # Will be executed before the first test
    yield
    # Will be executed after the last test
    mock_app.backend.db[mock_app.config["MONGO_DB_NAME"]].drop()
