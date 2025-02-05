import pytest
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro_graphql.asgi import KedroGraphQL
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.models import Pipeline, DataSet, Parameter, Tag, State, PipelineStatus
from unittest.mock import patch
import shutil
import os

@pytest.fixture(scope="session")
def kedro_session():
    bootstrap_project(Path.cwd())
    return KedroSession.create()

@pytest.fixture(scope="session")
def mock_app(kedro_session):
    app = KedroGraphQL(kedro_session = kedro_session)
    app.config["LOG_PATH_PREFIX"]="src/tests/tmp"
    return app

@pytest.fixture(scope="session", autouse=True)
def cleanup_tmp_directory():
    """Fixture to clean up all files in src/tests/tmp after each test."""
    tmp_dir = "src/tests/tmp" # Should match LOG_PATH_PREFIX
    
    yield  # The test runs here
    
    # Clean up the tmp directory after the test completes
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

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


## refer to https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html for info on tmp_path fixture
@pytest.fixture
def mock_text_in(tmp_path):
    #tmp_path.mkdir()
    text_in = tmp_path / "text_in.txt"
    text_in.write_text("hello")
    return text_in

@pytest.fixture
def mock_text_out(tmp_path):
    #tmp_path.mkdir()
    text_out = tmp_path / "text_out.txt"
    text_out.write_text("good bye")
    return text_out

@pytest.fixture
def mock_text_in_tsv(tmp_path):
    #tmp_path.mkdir()
    text = tmp_path / "text_in.tsv"
    text.write_text("Some parameter\tOther parameter\tLast parameter\nCONST\t123456\t12.45")
    return text

@pytest.fixture
def mock_text_out_tsv(tmp_path):
    #tmp_path.mkdir()
    text = tmp_path / "text_out.tsv"
    text.write_text("Some parameter\tOther parameter\tLast parameter\nCONST\t123456\t12.45")
    return text

@pytest.mark.usefixtures('mock_celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('depends_on_current_app')
@pytest.fixture
def mock_pipeline(mock_app, tmp_path, mock_text_in, mock_text_out):

    data_catalog = [{"name": "text_in","config": "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/01_raw/text_in.txt\"}"},{"name": "text_out","config": "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/02_intermediate/text_out.txt\"}"}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        data_catalog=[DataSet.from_dict(d) for d in data_catalog],
        parameters = [Parameter(**p) for p in parameters],
        tags = [Tag(**p) for p in tags]
    )

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs = {"name": "example00", 
                                                 "data_catalog": serial["data_catalog"],
                                                 "parameters": serial["parameters"],
                                                 "runner": mock_app.config["KEDRO_GRAPHQL_RUNNER"]}, countdown=0.1)
    
    pipeline_status = PipelineStatus(state=State[result.status],
                                        runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                                        session=mock_app.kedro_session.session_id,
                                        started_at=None,
                                        finished_at=None,
                                        task_id=result.id,
                                        task_name=str(run_pipeline))

    p.status.append(pipeline_status)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p = mock_app.backend.create(p)
    return p

@pytest.fixture
def mock_pipeline2(mock_app, tmp_path, mock_text_in, mock_text_out):

    data_catalog = [{"name": "text_in","config": "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/01_raw/text_in.txt\"}"},{"name": "text_out","config": "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/02_intermediate/text_out.txt\"}"}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        data_catalog=[DataSet.from_dict(d) for d in data_catalog],
        parameters = [Parameter(**p) for p in parameters],
        tags = [Tag(**p) for p in tags]
    )

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs = {"name": "example00", 
                                                 "data_catalog": serial["data_catalog"],
                                                 "parameters": serial["parameters"],
                                                 "runner": mock_app.config["KEDRO_GRAPHQL_RUNNER"]}, countdown=0.1)

    pipeline_status = PipelineStatus(state=State[result.status],
                                        runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                                        session=mock_app.kedro_session.session_id,
                                        started_at=None,
                                        finished_at=None,
                                        task_id=result.id,
                                        task_name=str(run_pipeline))

    p.status.append(pipeline_status)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p = mock_app.backend.create(p)
    return p
