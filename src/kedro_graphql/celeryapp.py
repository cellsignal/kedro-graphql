from celery import Celery
from celery import signals

from .config import KedroGraphQLConfig


def celery_app(config: KedroGraphQLConfig, backend):
    app = Celery()

    class Config:
        broker_url = config.broker
        result_backend = config.celery_result_backend
        result_extended = True
        task_serializer = 'json'
        result_serializer = 'json'
        accept_content = ['json']
        enable_utc = True
        worker_send_task_events = True
        task_send_sent_event = True
        imports = "kedro_graphql.tasks"
        worker_soft_shutdown_timeout = 10
        broker_connection_retry_on_startup = True

    app.config_from_object(Config)
    app.kedro_graphql_backend = backend
    app.kedro_graphql_config = config
    return app


@signals.setup_logging.connect
def on_setup_logging(**kwargs):
    #  Disable Celery logging configuration so logs are captured in info.log and error.log
    # https://docs.celeryq.dev/en/latest/userguide/tasks.html#logging
    pass
