import os
import tempfile

from dotenv import dotenv_values
import json
import yaml
from importlib import import_module
from .logs.logger import logger


def load_api_spec(spec):
    """Load API configuration from yaml file."""
    # load the UI yaml specification
    with open(spec) as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.error(str(exc))

    # import additinal modules to enable plugin discovery
    # e.g. @gql_form, @gql_data, etc...
    imports = [i.strip() for i in conf["config"]["imports"]]
    for i in imports:
        import_module(i)

    config = {"_".join(["KEDRO_GRAPHQL", k.upper()]): v for k,
              v in conf["config"].items()}

    return config


config = {
    "KEDRO_GRAPHQL_MONGO_URI": "mongodb://root:example@localhost:27017/",
    "KEDRO_GRAPHQL_MONGO_DB_NAME": "pipelines",
    "KEDRO_GRAPHQL_MONGO_DB_COLLECTION": "pipelines",
    "KEDRO_GRAPHQL_IMPORTS": "kedro_graphql.plugins.plugins,",
    "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphQL",
    "KEDRO_GRAPHQL_APP_TITLE": "Kedro GraphQL API",
    "KEDRO_GRAPHQL_APP_DESCRIPTION": "A tool for serving kedro projects as a GraphQL API",
    "KEDRO_GRAPHQL_PROJECT_VERSION": "None",
    "KEDRO_GRAPHQL_BACKEND": "kedro_graphql.backends.mongodb.MongoBackend",
    "KEDRO_GRAPHQL_BROKER": "redis://localhost",
    "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": "redis://localhost",
    "KEDRO_GRAPHQL_PERMISSIONS": "kedro_graphql.permissions.IsAuthenticatedXForwardedEmail",
    "KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAPPING": "EXTERNAL_GROUP_NAME=admin",
    # kedro_graphql.runner.argo.ArgoWorkflowsRunner
    "KEDRO_GRAPHQL_RUNNER": "kedro.runner.SequentialRunner",
    "KEDRO_GRAPHQL_ENV": "local",
    "KEDRO_GRAPHQL_CONF_SOURCE": None,
    "KEDRO_GRAPHQL_DEPRECATIONS_DOCS": "https://github.com/opensean/kedro-graphql/blob/main/README.md#deprecations",
    "KEDRO_GRAPHQL_LOG_TMP_DIR": tempfile.TemporaryDirectory().name,
    "KEDRO_GRAPHQL_LOG_PATH_PREFIX": None,
    "KEDRO_GRAPHQL_EVENTS_CONFIG": None,

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
