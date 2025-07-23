from kedro_graphql.config import load_config


def kedro_graphql_config():

    config = load_config()

    # enable events endpoint
    config["KEDRO_GRAPHQL_EVENTS_CONFIG"] = {"event00": {
        "source": "example.com", "type": "com.example.event"}}

    # use "test_pipelines" as the collection name for testing
    config["KEDRO_GRAPHQL_MONGO_DB_COLLECTION"] = "test_pipelines"
    config["KEDRO_GRAPHQL_MONGO_DB_NAME"] = "test_pipelines"

    return config
