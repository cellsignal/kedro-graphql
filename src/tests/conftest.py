import pytest
from pathlib import Path
from kedro.framework.project import settings
from kedro.config import ConfigLoader
from kedro.framework.context import KedroContext
from kedro.framework.hooks import _create_hook_manager
from kedro_graphql.config import backend, backend_kwargs
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.models import Pipeline, DataSet, Parameter
from unittest.mock import patch



@pytest.fixture(scope="session")
def config_loader():
    return ConfigLoader(conf_source=str(Path.cwd() / settings.CONF_SOURCE))


@pytest.fixture(scope='session')
def project_context(config_loader):
    return KedroContext(
        package_name="kedro_graphql",
        project_path=Path.cwd(),
        config_loader=config_loader,
        hook_manager=_create_hook_manager(),
    )

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
        'imports': ["kedro_graphql.config", "kedro_graphql.tasks"]

    }


@pytest.fixture(scope="session")
def celery_worker_parameters():
    return {"without_heartbeat": False}

@pytest.fixture
def mock_backend():
    return backend(**backend_kwargs)

@pytest.fixture
def mock_info_context(mock_backend):
    class App():
        backend = mock_backend

    class Request():
        app = App()

    with patch("strawberry.types.Info.context", {"request": Request()}) as m:
        yield m

@pytest.fixture
def mock_pipeline(mock_backend):

    inputs = [{"name": "text_in", "type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}]
    outputs = [{"name":"text_out", "type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}]
    parameters = [{"name":"example", "value":"hello"}]

    p = Pipeline(
        name = "example00",
        inputs = [DataSet(**i) for i in inputs],
        outputs = [DataSet(**o) for o in outputs],
        parameters = [Parameter(**p) for p in parameters],
        task_name = str(run_pipeline),
    )

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs = {"name": "example00", 
                                                 "inputs": inputs, 
                                                 "outputs": outputs,
                                                 "parameters": parameters}, countdown=1)
    p.task_id = result.id
    p.status = result.status
    p.task_kwargs = str(
            {"name": serial["name"], 
            "inputs": serial["inputs"], 
            "outputs": serial["outputs"], 
            "parameters": serial["parameters"]}
    )

    print(f'Starting {p.name} pipeline with task_id: ' + str(p.task_id))
    p = mock_backend.create(p)
    return p