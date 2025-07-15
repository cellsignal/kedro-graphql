import os
import tempfile

from dotenv import dotenv_values
import json
import yaml
from importlib import import_module
from .logs.logger import logger
import copy


defaults = {
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
    # kedro_graphql.runner.argo.ArgoWorkflowsRunner
    "KEDRO_GRAPHQL_RUNNER": "kedro.runner.SequentialRunner",
    "KEDRO_GRAPHQL_ENV": "local",
    "KEDRO_GRAPHQL_CONF_SOURCE": None,
    "KEDRO_GRAPHQL_DEPRECATIONS_DOCS": "https://github.com/opensean/kedro-graphql/blob/main/README.md#deprecations",
    "KEDRO_GRAPHQL_LOG_TMP_DIR": tempfile.TemporaryDirectory().name,
    "KEDRO_GRAPHQL_LOG_PATH_PREFIX": None,
    "KEDRO_GRAPHQL_SIGNED_URL_PROVIDER": "kedro_graphql.plugins.presigned_url.s3_provider.S3PreSignedUrlProvider",
    "KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC": 43200,
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL": "http://localhost:5000",
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY": "my-secret-key",
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM": "HS256",
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS": ["./data", "/var", "/tmp"],
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS": ["./data"],
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB": 10,
    "KEDRO_GRAPHQL_EVENTS_CONFIG": None,
    "KEDRO_GRAPHQL_PERMISSIONS": "kedro_graphql.permissions.IsAuthenticatedAlways",
    # "KEDRO_GRAPHQL_PERMISSIONS": "kedro_graphql.permissions.IsAuthenticatedXForwardedEmail",
    "KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP": {
        "admin": ["create_pipeline",
                  "read_pipeline",
                  "read_pipelines",
                  "update_pipeline",
                  "delete_pipeline",
                  "read_pipeline_template",
                  "read_pipeline_templates",
                  "create_dataset",
                  "read_dataset",
                  "subscribe_to_events",
                  "subscribe_to_logs",
                  "create_event"]
    },
}


def load_api_spec():
    """Load API configuration from yaml file."""
    # load the UI yaml specification
    spec = os.environ.get("KEDRO_GRAPHQL_API_SPEC", None)
    if spec:
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
    else:
        logger.debug("No API spec file found. Using default configuration.")
        return {}

# special parsing


def env_var_parser(config):
    if config.get("KEDRO_GRAPHQL_EVENTS_CONFIG", None):
        if isinstance(config["KEDRO_GRAPHQL_EVENTS_CONFIG"], str):
            config["KEDRO_GRAPHQL_EVENTS_CONFIG"] = json.loads(
                (config["KEDRO_GRAPHQL_EVENTS_CONFIG"]))
    if config.get("KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP", None):
        if isinstance(config["KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP"], str):
            config["KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP"] = json.loads(
                (config["KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP"]))
    if config.get("KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP", None):
        if isinstance(config["KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP"], str):
            config["KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP"] = json.loads(
                (config["KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP"]))
    return config


def load_config():
    """Load configuration from the environment variables and API spec."""
    config = {
        **copy.deepcopy(defaults),  # defaults
        **dotenv_values(".env"),  # .env file
        **load_api_spec(),  # loaded API spec
        **os.environ,  # override loaded values with environment variables
    }
    config = env_var_parser(config)  # special parsing for any environment variables
    return config
