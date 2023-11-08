from celery import Celery


def celery_app(config, backend):
    app = Celery()
    
    class Config:
        broker_url = config["KEDRO_GRAPHQL_BROKER"]
        result_backend = config["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"]
        result_extended = True
        task_serializer = 'json'
        result_serializer = 'json'
        accept_content = ['json']
        enable_utc = True
        worker_send_task_events = True
        task_send_sent_event = True
        imports = "kedro_graphql.tasks"
    
    app.config_from_object(Config)
    app.kedro_graphql_backend = backend
    return app