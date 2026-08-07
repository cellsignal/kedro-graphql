from kedro_graphql.config import load_config


def kedro_graphql_config():
    return load_config().model_copy(
        update={
            "events_config": {
                "event00": {
                    "source": "example.com",
                    "type": "com.example.event",
                }
            },
            "mongo_db_collection": "test_pipelines",
            "mongo_db_name": "test_pipelines",
            "broker": "redis://localhost:6379/15",
            "celery_result_backend": "redis://localhost:6379/15",
        }
    )
