import pytest
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro_graphql.asgi import KedroGraphQL
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.models import Pipeline, DataSet, Parameter, Tag, State, PipelineStatus
from unittest.mock import patch
from datetime import datetime
import json

@pytest.fixture(scope="session")
def kedro_session():
    bootstrap_project(Path.cwd())
    return KedroSession.create()

@pytest.fixture(scope="session")
def mock_app(kedro_session):
    return KedroGraphQL(kedro_session = kedro_session)

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

    inputs = [{"name": "text_in", "type": "text.TextDataset", "filepath": str(mock_text_in)}]
    outputs = [{"name":"text_out", "type": "text.TextDataset", "filepath": str(mock_text_out)}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        inputs = [DataSet(**i) for i in inputs],
        outputs = [DataSet(**o) for o in outputs],
        parameters = [Parameter(**p) for p in parameters],
        tags = [Tag(**p) for p in tags]
    )

    p.status.append(PipelineStatus(state=State.READY,
                                        runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                                        session=mock_app.kedro_session.session_id,
                                        started_at=datetime.now(),
                                        task_name=str(run_pipeline)))

    p.created_at = datetime.now()
    p = mock_app.backend.create(p)

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs = { "id": str(p.id),
                                                 "name": "example00", 
                                                 "inputs": serial["inputs"], 
                                                 "outputs": serial["outputs"],
                                                 "parameters": serial["parameters"],
                                                 "runner": mock_app.config["KEDRO_GRAPHQL_RUNNER"]}, 
                                      countdown=0.1)
    
    
    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p.status[-1].task_id = result.id
    p = mock_app.backend.update(p)
    return p

@pytest.fixture
def mock_pipeline2(mock_app, tmp_path, mock_text_in, mock_text_out):

    inputs = [{"name": "text_in", "type": "text.TextDataset", "filepath": str(mock_text_in)}]
    outputs = [{"name":"text_out", "type": "text.TextDataset", "filepath": str(mock_text_out)}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        inputs = [DataSet(**i) for i in inputs],
        outputs = [DataSet(**o) for o in outputs],
        parameters = [Parameter(**p) for p in parameters],
        tags = [Tag(**p) for p in tags]
    )

    p.status.append(PipelineStatus(state=State.READY,
                                        runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                                        session=mock_app.kedro_session.session_id,
                                        started_at=datetime.now(),
                                        task_name=str(run_pipeline)))

    p.created_at = datetime.now()
    p = mock_app.backend.create(p)

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs = { "id": str(p.id),
                                                 "name": "example00", 
                                                 "inputs": serial["inputs"], 
                                                 "outputs": serial["outputs"],
                                                 "parameters": serial["parameters"],
                                                 "runner": mock_app.config["KEDRO_GRAPHQL_RUNNER"]}, 
                                      countdown=0.1)

    print(f'Starting {p.name} pipeline with task_id: ' + str(result.id))
    p.status[-1].task_id = result.id
    p = mock_app.backend.update(p)
    return p

@pytest.fixture
def mock_pipeline_no_task(mock_app, mock_text_in, mock_text_out):

    inputs = [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name":"text_out", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_out)})}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        data_catalog= [DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters = [Parameter(**p) for p in parameters],
        tags = [Tag(**p) for p in tags]
    )

    p.status.append(PipelineStatus(state=State.READY,
                                        runner=mock_app.config["KEDRO_GRAPHQL_RUNNER"],
                                        session=mock_app.kedro_session.session_id,
                                        started_at=datetime.now(),
                                        task_name=str(run_pipeline)))

    p.created_at = datetime.now()
    return p