from kedro_graphql.config import load_config


def kedro_graphql_config():

    config = load_config()

    # enable events endpoint
    config["KEDRO_GRAPHQL_EVENTS_CONFIG"] = {"event00": {
        "source": "example.com", "type": "com.example.event"}}

    # use "test_pipelines" as the collection name for testing
    config["KEDRO_GRAPHQL_MONGO_DB_COLLECTION"] = "test_pipelines"
    config["KEDRO_GRAPHQL_MONGO_DB_NAME"] = "test_pipelines"

    # Use an isolated Redis DB for tests so test runs do not pollute local/dev keys.
    config["KEDRO_GRAPHQL_BROKER"] = "redis://localhost:6379/15"
    config["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"] = "redis://localhost:6379/15"

    return config
