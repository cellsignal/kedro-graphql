import os
import pathlib
from importlib import import_module

import click
import uvicorn
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from watchfiles import run_process

from .config import load_config, cli_config
from .logs.logger import logger


def init_app(app, config, session):
    # create app instance
    module, class_name = app.rsplit(".", 1)
    module = import_module(module)
    class_inst = getattr(module, class_name)
    return class_inst(kedro_session=session, config=config)


def start_app(app, config, conf_source, env, package_name, project_path):
    bootstrap_project(project_path)
    with KedroSession.create(project_path=project_path, env=env, conf_source=conf_source) as session:
        a = init_app(app, config, session)
        uvicorn.run(a, host="0.0.0.0", port=5000, log_level="info")


def start_worker(app, config, conf_source, env, package_name, project_path):

    bootstrap_project(project_path)
    with KedroSession.create(project_path=project_path, env=env, conf_source=conf_source) as session:
        a = init_app(app, config, session)
        worker = a.celery_app.Worker()
        worker.start()


@click.group(name="kedro-graphql")
def commands():
    pass


@commands.command()
@click.pass_obj
@click.option("--app", "-a", default=None, help="Application import path")
@click.option("--app-title", default=None, help="Title of the Kedro GraphQL application")
@click.option("--app-description", default=None, help="Description of the Kedro GraphQL application")
@click.option("--backend", default=None, help="The only supported value for this option is 'kedro_graphql.backends.mongodb.MongoBackend'")
@click.option("--broker", default=None, help="URI to broker e.g. 'redis://localhost'")
@click.option("--celery-result-backend", default=None, help="URI to backend for celery results e.g. 'redis://localhost'")
@click.option("--client-uri-graphql", default=None, help="URI for GraphQL API endpoint used by the GraphQL client")
@click.option("--client-uri-ws", default=None, help="URI for WebSocket endpoint used by the GraphQL client for subscriptions")
@click.option("--conf-source", default=None, help="Path of a directory where project configuration is stored.")
@click.option("--dataset-filepath-masks", default=None, help="List of masks to apply to Dataset filepaths before returning responses to client to hide true location of datasets (JSON string)")
@click.option("--dataset-filepath-allowed-roots", default=None, help="List of allowed root directories for Dataset filepaths (JSON string)")
@click.option("--deprecations-docs", default=None, help="URL to documentation about deprecated features")
@click.option("--env", "-e", default=None, help="Kedro configuration environment name. Defaults to `local`.")
@click.option("--events-config", default=None, help="Event configuration as JSON string")
@click.option("--imports", "-i", default=None, help="Additional import paths (comma-separated string or JSON array)")
@click.option("--local-file-provider-download-allowed-roots", default=None, help="Allowed root directories for downloads (comma-separated string or JSON array)")
@click.option("--local-file-provider-jwt-algorithm", default=None, help="Algorithm used for JWT signing (e.g., 'HS256')")
@click.option("--local-file-provider-jwt-secret-key", default=None, help="Secret key for signing JWT tokens for local file access")
@click.option("--local-file-provider-server-url", default=None, help="Base URL for the local file server")
@click.option("--local-file-provider-upload-allowed-roots", default=None, help="Allowed root directories for uploads (comma-separated string or JSON array)")
@click.option("--local-file-provider-upload-max-file-size-mb", default=None, type=int, help="Maximum allowed upload file size in megabytes")
@click.option("--log-path-prefix", default=None, help="Prefix of path to save logs")
@click.option("--log-tmp-dir", default=None, help="Temporary directory for logs")
@click.option("--mongo-db-collection", default=None, help="Name of the MongoDB collection to use")
@click.option("--mongo-db-name", default=None, help="Name to use for collection in mongo e.g. 'pipelines'")
@click.option("--mongo-uri", default=None, help="URI to mongodb e.g. 'mongodb://root:example@localhost:27017/'")
@click.option("--permissions", default=None, help="Python path to the permissions class used for authentication")
@click.option("--permissions-group-to-role-map", default=None, help="Mapping of external group names to roles as JSON string")
@click.option("--permissions-role-to-action-map", default=None, help="Mapping of roles to allowed actions as JSON string")
@click.option("--project-version", default=None, help="Version of the Kedro GraphQL project")
@click.option("--root-path", default=None, help="Root path for API endpoints (e.g., '/api/v1')")
@click.option("--runner", default=None, help="Execution mechanism to run pipelines e.g. 'kedro.runner.SequentialRunner'")
@click.option("--signed-url-max-expires-in-sec", default=None, type=int, help="Maximum allowed expiration time (in seconds) for presigned URLs")
@click.option("--signed-url-provider", default=None, help="Python path to the presigned URL provider class")
@click.option("--reload", "-r", is_flag=True, default=False, help="Enable auto-reload.")
@click.option("--reload-path", default=None, type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path), help="Path to watch for file changes, defaults to <project path>/src")
@click.option("--api-spec", default=None, type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path), help="Path to YAML API specification file")
@click.option("--ui", "-u", is_flag=True, default=False, help="Start a viz app.")
@click.option("--ui-spec", default="", help="UI YAML specification file")
@click.option("--worker", "-w", is_flag=True, default=False, help="Start a celery worker.")
def gql(metadata, app, app_title, app_description, backend, broker, celery_result_backend, client_uri_graphql, client_uri_ws, conf_source,
        dataset_filepath_masks, dataset_filepath_allowed_roots, deprecations_docs, env, events_config, imports,
        local_file_provider_download_allowed_roots,
        local_file_provider_jwt_algorithm, local_file_provider_jwt_secret_key, local_file_provider_server_url,
        local_file_provider_upload_allowed_roots, local_file_provider_upload_max_file_size_mb,
        log_path_prefix, log_tmp_dir, mongo_db_collection, mongo_db_name, mongo_uri, permissions,
        permissions_group_to_role_map, permissions_role_to_action_map, project_version, root_path, runner,
        signed_url_max_expires_in_sec, signed_url_provider,
        reload, reload_path, api_spec, ui, ui_spec, worker):
    """Commands for working with kedro-graphql."""

    # inject CLI options into config before calling load_config() to ensure all modules get same config
    if api_spec:
        os.environ["KEDRO_GRAPHQL_API_SPEC"] = str(api_spec)
    if app:
        cli_config["KEDRO_GRAPHQL_APP"] = app
    if app_title:
        cli_config["KEDRO_GRAPHQL_APP_TITLE"] = app_title
    if app_description:
        cli_config["KEDRO_GRAPHQL_APP_DESCRIPTION"] = app_description
    if backend:
        cli_config["KEDRO_GRAPHQL_BACKEND"] = backend
    if broker:
        cli_config["KEDRO_GRAPHQL_BROKER"] = broker
    if celery_result_backend:
        cli_config["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"] = celery_result_backend
    if client_uri_graphql:
        cli_config["KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL"] = client_uri_graphql
    if client_uri_ws:
        cli_config["KEDRO_GRAPHQL_CLIENT_URI_WS"] = client_uri_ws
    if conf_source:
        cli_config["KEDRO_GRAPHQL_CONF_SOURCE"] = conf_source
    if dataset_filepath_masks:
        cli_config["KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS"] = dataset_filepath_masks
    if dataset_filepath_allowed_roots:
        cli_config["KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS"] = dataset_filepath_allowed_roots
    if deprecations_docs:
        cli_config["KEDRO_GRAPHQL_DEPRECATIONS_DOCS"] = deprecations_docs
    if env:
        cli_config["KEDRO_GRAPHQL_ENV"] = env
    if events_config:
        cli_config["KEDRO_GRAPHQL_EVENTS_CONFIG"] = events_config
    if imports:
        cli_config["KEDRO_GRAPHQL_IMPORTS"] = imports
    if local_file_provider_download_allowed_roots:
        cli_config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS"] = local_file_provider_download_allowed_roots
    if local_file_provider_jwt_algorithm:
        cli_config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"] = local_file_provider_jwt_algorithm
    if local_file_provider_jwt_secret_key:
        cli_config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"] = local_file_provider_jwt_secret_key
    if local_file_provider_server_url:
        cli_config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL"] = local_file_provider_server_url
    if local_file_provider_upload_allowed_roots:
        cli_config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS"] = local_file_provider_upload_allowed_roots
    if local_file_provider_upload_max_file_size_mb is not None:
        cli_config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB"] = local_file_provider_upload_max_file_size_mb
    if log_path_prefix:
        cli_config["KEDRO_GRAPHQL_LOG_PATH_PREFIX"] = log_path_prefix
    if log_tmp_dir:
        cli_config["KEDRO_GRAPHQL_LOG_TMP_DIR"] = log_tmp_dir
    if mongo_db_collection:
        cli_config["KEDRO_GRAPHQL_MONGO_DB_COLLECTION"] = mongo_db_collection
    if mongo_db_name:
        cli_config["KEDRO_GRAPHQL_MONGO_DB_NAME"] = mongo_db_name
    if mongo_uri:
        cli_config["KEDRO_GRAPHQL_MONGO_URI"] = mongo_uri
    if permissions:
        cli_config["KEDRO_GRAPHQL_PERMISSIONS"] = permissions
    if permissions_group_to_role_map:
        cli_config["KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP"] = permissions_group_to_role_map
    if permissions_role_to_action_map:
        cli_config["KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP"] = permissions_role_to_action_map
    if project_version:
        cli_config["KEDRO_GRAPHQL_PROJECT_VERSION"] = project_version
    if root_path:
        cli_config["KEDRO_GRAPHQL_ROOT_PATH"] = root_path
    if runner:
        cli_config["KEDRO_GRAPHQL_RUNNER"] = runner
    if signed_url_max_expires_in_sec is not None:
        cli_config["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"] = signed_url_max_expires_in_sec
    if signed_url_provider:
        cli_config["KEDRO_GRAPHQL_SIGNED_URL_PROVIDER"] = signed_url_provider

    os.environ["KEDRO_GRAPHQL_PROJECT_VERSION"] = getattr(
        import_module(metadata.package_name), "__version__", None)
    os.environ["KEDRO_PROJECT_NAME"] = metadata.package_name

    config = load_config()
    logger.debug("configuration loaded by {s}".format(s=__name__))

    if not reload_path:
        reload_path = metadata.project_path.joinpath("src")

    if reload:
        logger.info("AUTO-RELOAD ACTIVATED, watching '" +
                    str(reload_path) + "' for changes")

    if ui:
        from .ui.app import start_ui
        if reload:
            run_process(str(reload_path), target=start_ui, kwargs={
                        "spec": ui_spec, "config": config})
        else:
            start_ui(spec=ui_spec, config=config)

    elif worker:
        if reload:
            run_process(str(reload_path), target=start_worker, args=(
                config["KEDRO_GRAPHQL_APP"], config, config["KEDRO_GRAPHQL_CONF_SOURCE"], config["KEDRO_GRAPHQL_ENV"], metadata.package_name, metadata.project_path))
        else:
            start_worker(config["KEDRO_GRAPHQL_APP"], config, config["KEDRO_GRAPHQL_CONF_SOURCE"], config["KEDRO_GRAPHQL_ENV"],
                         metadata.package_name, metadata.project_path)

    else:
        if reload:
            run_process(reload_path, target=start_app, args=(config["KEDRO_GRAPHQL_APP"], config, config["KEDRO_GRAPHQL_CONF_SOURCE"],
                        config["KEDRO_GRAPHQL_ENV"], metadata.package_name, metadata.project_path))
        else:
            start_app(config["KEDRO_GRAPHQL_APP"], config, config["KEDRO_GRAPHQL_CONF_SOURCE"], config["KEDRO_GRAPHQL_ENV"],
                      metadata.package_name, metadata.project_path)
