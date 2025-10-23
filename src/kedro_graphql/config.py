import os
import tempfile

from dotenv import dotenv_values
import json
import yaml
from importlib import import_module
from .logs.logger import logger
import copy


defaults = {
    "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphQL",
    "KEDRO_GRAPHQL_APP_DESCRIPTION": "A tool for serving kedro projects as a GraphQL API",
    "KEDRO_GRAPHQL_APP_TITLE": "Kedro GraphQL API",
    "KEDRO_GRAPHQL_BACKEND": "kedro_graphql.backends.mongodb.MongoBackend",
    "KEDRO_GRAPHQL_BROKER": "redis://localhost",
    "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": "redis://localhost",
    "KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL": "http://localhost:5000/graphql",
    "KEDRO_GRAPHQL_CLIENT_URI_WS": "ws://localhost:5000/graphql",
    "KEDRO_GRAPHQL_CONF_SOURCE": None,
    "KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS": [],
    "KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS": [],
    "KEDRO_GRAPHQL_DEPRECATIONS_DOCS": None,
    "KEDRO_GRAPHQL_ENV": "local",
    "KEDRO_GRAPHQL_EVENTS_CONFIG": None,
    "KEDRO_GRAPHQL_IMPORTS": ["kedro_graphql.plugins.plugins"],
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS": ["./data", "/var", "/tmp"],
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM": "HS256",
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY": "my-secret-key",
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL": "http://localhost:5000",
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS": ["./data"],
    "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB": 10,
    "KEDRO_GRAPHQL_LOG_PATH_PREFIX": None,
    "KEDRO_GRAPHQL_LOG_TMP_DIR": tempfile.TemporaryDirectory().name,
    "KEDRO_GRAPHQL_MONGO_DB_COLLECTION": "pipelines",
    "KEDRO_GRAPHQL_MONGO_DB_NAME": "pipelines",
    "KEDRO_GRAPHQL_MONGO_URI": "mongodb://root:example@localhost:27017/",
    "KEDRO_GRAPHQL_PERMISSIONS": "kedro_graphql.permissions.IsAuthenticatedAlways",
    "KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP": {
        # "KEDRO_GRAPHQL_PERMISSIONS": "kedro_graphql.permissions.IsAuthenticatedXForwardedEmail",
        "EXTERNAL_GROUP_NAME": "admin"
    },
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
    "KEDRO_GRAPHQL_PROJECT_VERSION": "None",
    "KEDRO_GRAPHQL_ROOT_PATH": "",
    "KEDRO_GRAPHQL_RUNNER": "kedro.runner.SequentialRunner",
    # "KEDRO_GRAPHQL_RUNNER": "kedro_graphql.runner.argo.ArgoWorkflowsRunner",
    "KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC": 43200,
    "KEDRO_GRAPHQL_SIGNED_URL_PROVIDER": "kedro_graphql.signed_url.s3_provider.S3Provider",
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
                return {}

        # import additinal modules to enable plugin discovery
        # e.g. @gql_form, @gql_data, etc...
        imports = conf["config"]["imports"]
        if isinstance(imports, str):
            # Handle comma-separated string
            imports = [i.strip() for i in imports.split(',') if i.strip()]
        elif isinstance(imports, list):
            # Already a list, just ensure strings are stripped
            imports = [i.strip() for i in imports if i.strip()]

        for i in imports:
            import_module(i)

        config = {"_".join(["KEDRO_GRAPHQL", k.upper()]): v for k,
                  v in conf["config"].items()}

        return config
    else:
        logger.debug("No API spec file found. Using default configuration.")
        return {}


cli_config = {}  # placeholder for CLI config


def env_var_parser(config):
    # Parse JSON strings for complex data types
    json_fields = [
        "KEDRO_GRAPHQL_EVENTS_CONFIG",
        "KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP",
        "KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP",
        "KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS",
        "KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS",
    ]

    # Fields that can be either JSON arrays, comma-separated strings, or lists
    list_fields = [
        "KEDRO_GRAPHQL_IMPORTS",
        "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS",
        "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS",
    ]

    for field in json_fields:
        if config.get(field, None) and isinstance(config[field], str):
            try:
                config[field] = json.loads(config[field])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for {field}: {config[field]}")

    # Handle list fields. Can be string (comma-separated) or list or JSON array
    for field in list_fields:
        if field in config:
            value = config[field]
            if isinstance(value, str):
                if value.strip():
                    # Try to parse as JSON first
                    try:
                        config[field] = json.loads(value)
                    except json.JSONDecodeError:
                        # If not JSON, treat as comma-separated string
                        config[field] = [i.strip()
                                         for i in value.split(',') if i.strip()]
                else:
                    # Empty string should become empty list
                    config[field] = []
    return config


def load_config(cli_config=cli_config):
    """Load configuration from the environment variables and API spec.

    Configuration precedence (highest to lowest):
    1. YAML API spec
    2. CLI flags
    3. Environment variables
    4. .env file
    5. Defaults
    """

    config = {
        **copy.deepcopy(defaults),  # defaults (lowest precedence)
        **dotenv_values(".env"),  # .env file
        **os.environ,  # environment variables
        **cli_config,  # CLI flags (higher precedence than env vars)
        **load_api_spec(),  # YAML API spec (highest precedence)
    }
    config = env_var_parser(config)  # special parsing for any environment variables

    return config
