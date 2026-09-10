import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import redis

import pytest
from kedro.framework.startup import bootstrap_project

from kedro_graphql.asgi import create_app
from kedro_graphql.models import (
    DataSet,
    Parameter,
    Pipeline,
    PipelineStatus,
    State,
    Tag,
)
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.utils import run_sync
from fastapi.middleware.cors import CORSMiddleware
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.context import GraphQLContext
from multiprocessing import Process
import uvicorn
from kedro_graphql.project import load_project_metadata
import multiprocessing as mp
import tempfile
import pytest_asyncio
from .utilities import kedro_graphql_config


if mp.get_start_method(allow_none=True) != "spawn":
    mp.set_start_method("spawn")


@pytest.fixture(scope="session")
def project_metadata():
    bootstrap_project(Path.cwd())
    return load_project_metadata(Path.cwd(), kedro_graphql_config())


def start_server(port=5000, config={}):

    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory() as tmp2:
            bootstrap_project(Path.cwd())
            metadata = load_project_metadata(Path.cwd(), config)
            config = config.model_copy(
                update={"log_path_prefix": tmp, "log_tmp_dir": tmp2}
            )
            app = create_app(config, metadata)
            # print("Starting Kedro GraphQL server with config: ", app.config)
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            uvicorn.run(app,
                        host="localhost",
                        port=port)


@pytest.fixture(scope="session")
def mock_server():
    config = kedro_graphql_config()
    proc = Process(target=start_server, args=(), kwargs={
                   "port": 5000,
                   "config": config})
    proc.start()
    yield
    proc.terminate()


@pytest.fixture(scope="session")
def mock_server_5001():
    config = kedro_graphql_config()
    config = config.model_copy(update={
        "permissions": "kedro_graphql.permissions.IsAuthenticatedXForwardedRBAC",
        "permissions_group_to_role_map": {"test_group": "admin"},
    })

    proc = Process(target=start_server, args=(), kwargs={
                   "port": 5001,
                   "config": config})
    proc.start()
    yield
    proc.terminate()


@pytest.fixture(scope="session")
def mock_server_5002():
    config = kedro_graphql_config()
    config = config.model_copy(update={
        "permissions": "kedro_graphql.permissions.IsAuthenticatedXForwardedEmail",
        "permissions_group_to_role_map": {"test_group": "admin"},
    })

    proc = Process(target=start_server, args=(), kwargs={
                   "port": 5002,
                   "config": config})
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
def mock_app(project_metadata):
    config = kedro_graphql_config()
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory() as tmp2:
            config = config.model_copy(update={
                "log_path_prefix": tmp,
                "log_tmp_dir": tmp2,
                "celery_abort_polling_interval": 1,
                "celery_abort_grace_period": 5,
            })
            app = create_app(config, project_metadata)

            yield app


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://localhost:6379/15',
        'result_backend': 'redis://localhost:6379/15',
        'result_extended': True,
        'worker_send_task_events': True,
        'task_send_sent_event': True,
        'task_store_eager_result': True,
        'task_always_eager': False,
        'task_ignore_result': False,
        'imports': ["kedro_graphql.tasks"]

    }


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_redis():
    """Ensure Redis keys created by tests are cleaned up before and after the session."""
    connection = redis.Redis.from_url("redis://localhost:6379/15")
    connection.flushdb()
    yield
    connection.flushdb()


@pytest.fixture(scope='session')
def mock_celery_session_app(mock_app, mock_info_context, celery_session_app):
    celery_session_app.kedro_graphql_backend = mock_app.state.services.backend
    celery_session_app.kedro_graphql_config = mock_app.state.services.config
    return celery_session_app


@pytest.fixture(scope="session")
def celery_worker_parameters():
    return {"without_heartbeat": False}


@pytest.fixture(scope="session")
def mock_info_context(mock_app):

    class Request():
        app = mock_app
        headers = {}

    context = GraphQLContext(Request())
    with patch("strawberry.types.Info.context", context):
        yield context


@pytest.fixture(scope="session")
def mock_info(mock_info_context):
    return SimpleNamespace(context=mock_info_context)


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
        parameters=[Parameter.from_dict(p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.READY,
                               runner=mock_app.state.services.config.runner,
                               session="test-session",
                               started_at=datetime.now(timezone.utc),
                               task_name=str(run_pipeline))]
    )

    p.created_at = datetime.now(timezone.utc)
    p = run_sync(mock_app.state.services.backend.create(p))

    serial = p.to_kedro()

    result = run_pipeline.apply_async(kwargs={"id": str(p.id),
                                              "name": "example00",
                                              "data_catalog": serial["data_catalog"],
                                              "parameters": serial["parameters"],
                                              "runner": mock_app.state.services.config.runner},
                                      countdown=0.1)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p.status[-1].task_id = result.id
    p = run_sync(mock_app.state.services.backend.update(p))
    return p


@pytest.fixture
def mock_pipeline_staged(mock_app):

    inputs = [{"name": "text_in", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": "./data/01_raw/text_in.csv"})}]
    outputs = [{"name": "text_out", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": "./data/01_raw/text_out.csv"})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "opensean"}, {
        "key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example00",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter.from_dict(p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.STAGED,
                               runner=mock_app.state.services.config.runner,
                               session="test-session",
                               started_at=datetime.now(timezone.utc),
                               task_name=str(run_pipeline))]
    )

    p.created_at = datetime.now(timezone.utc)
    p = run_sync(mock_app.state.services.backend.create(p))
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
        parameters=[Parameter.from_dict(p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.READY,
                               runner=mock_app.state.services.config.runner,
                               session="test-session",
                               started_at=datetime.now(timezone.utc),
                               task_name=str(run_pipeline))]
    )

    p.created_at = datetime.now(timezone.utc)
    p = run_sync(mock_app.state.services.backend.create(p))

    serial = p.to_kedro()

    result = run_pipeline.apply_async(kwargs={"id": str(p.id),
                                              "name": "example00",
                                              "data_catalog": serial["data_catalog"],
                                              "parameters": serial["parameters"],
                                              "runner": mock_app.state.services.config.runner},
                                      countdown=0.1)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p.status[-1].task_id = result.id
    p = run_sync(mock_app.state.services.backend.update(p))
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
        parameters=[Parameter.from_dict(p) for p in parameters],
        tags=[Tag(**p) for p in tags]
    )

    p.status.append(PipelineStatus(state=State.READY,
                                   runner=mock_app.state.services.config.runner,
                                   session="test-session",
                                   started_at=datetime.now(timezone.utc),
                                   task_name=str(run_pipeline)))

    p.created_at = datetime.now(timezone.utc)
    return p


@pytest.fixture
def mock_timestamped_partitioned_dir(tmp_path):
    partitioned_dir = tmp_path / "timestamped_partitioned"
    partitioned_dir.mkdir(parents=True, exist_ok=True)
    (partitioned_dir / "part_00.txt").write_text("part 00")
    (partitioned_dir / "part_01.txt").write_text("part 01")
    return partitioned_dir


@pytest.fixture
def mock_example01(mock_app, mock_timestamped_partitioned_dir, mock_text_in):

    inputs = [{"name": "text_in", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name": "timestamped_partitioned", "config": json.dumps(
        {"type": "partitions.PartitionedDataset",
         "path": str(mock_timestamped_partitioned_dir),
         "filename_suffix": ".txt",
         "dataset": {"type": "text.TextDataset"}})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "harinlee83"}, {
        "key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example01",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter.from_dict(p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.STAGED,
                               runner=mock_app.state.services.config.runner,
                               session="test-session",
                               started_at=datetime.now(timezone.utc),
                               task_name=str(run_pipeline))]
    )

    p.created_at = datetime.now(timezone.utc)
    p = run_sync(mock_app.state.services.backend.create(p))
    return p


@pytest.fixture(autouse=True)
def delete_pipeline_collection(mock_app):
    # Will be executed before the first test
    yield
    # Will be executed after the last test

    async def _drop():
        db = mock_app.state.services.backend._get_collection().database
        await db[mock_app.state.services.config.mongo_db_name].drop()

    run_sync(_drop())
