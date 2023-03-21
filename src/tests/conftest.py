import pytest
from pathlib import Path
from kedro.framework.project import settings
from kedro.config import ConfigLoader
from kedro.framework.context import KedroContext
from kedro.framework.hooks import _create_hook_manager




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