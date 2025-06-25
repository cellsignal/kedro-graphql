import os
import pathlib
import tempfile

from dotenv import dotenv_values
import json

config = {
    "MONGO_URI": "mongodb://root:example@localhost:27017/",
    "MONGO_DB_NAME": "pipelines",
    "KEDRO_GRAPHQL_MONGO_DB_COLLECTION": "pipelines",
    "KEDRO_GRAPHQL_IMPORTS": "kedro_graphql.plugins.plugins,",
    "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphQL",
    "KEDRO_GRAPHQL_BACKEND": "kedro_graphql.backends.mongodb.MongoBackend",
    "KEDRO_GRAPHQL_BROKER": "redis://localhost",
    "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": "redis://localhost",
    # kedro_graphql.runner.argo.ArgoWorkflowsRunner
    "KEDRO_GRAPHQL_RUNNER": "kedro.runner.SequentialRunner",
    "KEDRO_GRAPHQL_ENV": "local",
    "KEDRO_GRAPHQL_CONF_SOURCE": None,
    "KEDRO_GRAPHQL_DEPRECATIONS_DOCS": "https://github.com/opensean/kedro-graphql/blob/main/README.md#deprecations",
    "KEDRO_GRAPHQL_LOG_TMP_DIR": tempfile.TemporaryDirectory().name,
    "KEDRO_GRAPHQL_LOG_PATH_PREFIX": None,

}

config = {
    **config,
    **dotenv_values(".env"),  # load
    **os.environ,  # override loaded values with environment variables
}

# special parsing

if config.get("KEDRO_GRAPHQL_EVENTS_CONFIG", None):
    if isinstance(config["KEDRO_GRAPHQL_EVENTS_CONFIG"], str):
        config["KEDRO_GRAPHQL_EVENTS_CONFIG"] = json.loads(
            (config["KEDRO_GRAPHQL_EVENTS_CONFIG"]))
