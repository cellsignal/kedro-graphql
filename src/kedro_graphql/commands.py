import pathlib
from importlib import import_module

import click
import uvicorn
from kedro.framework.startup import bootstrap_project
from watchfiles import run_process

from .backends import init_backend
from .celeryapp import celery_app
from .config import KedroGraphQLConfig, load_config
from .logs.logger import logger
from .project import load_project_metadata


def init_app(config: KedroGraphQLConfig, metadata):
    module_name, factory_name = config.app.rsplit(".", 1)
    factory = getattr(import_module(module_name), factory_name)
    return factory(config, metadata)


def start_app(config: KedroGraphQLConfig, project_path):
    bootstrap_project(project_path)
    metadata = load_project_metadata(project_path, config)
    app = init_app(config, metadata)
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")


def start_worker(config: KedroGraphQLConfig, project_path):
    bootstrap_project(project_path)
    backend = init_backend(config)
    celery_app(config, backend, project_path).Worker().start()


@click.group(name="kedro-graphql")
def commands():
    pass


@click.command(name="mongo-indexes")
@click.pass_context
@click.option("--apply", "apply_indexes", is_flag=True, help="Create configured indexes; never drop indexes.")
def mongo_indexes(ctx, apply_indexes):
    """List Mongo indexes, or explicitly create the configured definitions."""
    import json

    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    from .mongo_indexes import index_models

    config = ctx.meta["gql_config"]
    try:
        collections = index_models(config)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if apply_indexes and not collections:
        click.echo("No indexes configured; nothing to apply.")
        return
    collection = config.mongo_db_collection
    try:
        with MongoClient(config.mongo_uri, serverSelectionTimeoutMS=10000) as client:
            database = client[config.mongo_db_name]
            for collection in collections or {config.mongo_db_collection: []}:
                if apply_indexes:
                    names = database[collection].create_indexes(collections[collection])
                    click.echo(f"{collection}: ensured {', '.join(names)}")
                else:
                    indexes = list(database[collection].list_indexes())
                    click.echo(json.dumps({"collection": collection, "indexes": indexes}, default=str))
    except (PyMongoError, ValueError) as exc:
        # Driver errors can contain credentials from the connection URI.
        code = getattr(exc, "code", None)
        detail = f", code {code}" if code is not None else ""
        raise click.ClickException(
            f"Mongo index operation failed for {collection} ({type(exc).__name__}{detail}). "
            "No indexes were dropped; check Mongo diagnostics. Earlier creations may remain."
        ) from exc


@click.group(name="dataset-search")
def dataset_search_commands():
    """Inspect or rebuild catalog/tag search fields without changing their sources."""


def _maintain_dataset_search(ctx, rebuild):
    import json
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    from .dataset_search_maintenance import maintain_dataset_search

    config = ctx.meta["gql_config"]
    try:
        with MongoClient(config.mongo_uri, serverSelectionTimeoutMS=10000) as client:
            counts = maintain_dataset_search(client[config.mongo_db_name][config.mongo_db_collection], rebuild)
        click.echo(json.dumps(counts))
        if counts["failed"]:
            raise click.ClickException("Some records could not be inspected or rebuilt; see the reported counts.")
    except PyMongoError as error:
        raise click.ClickException(f"Dataset search maintenance failed ({type(error).__name__}); check Mongo diagnostics.") from error


@dataset_search_commands.command(name="check")
@click.pass_context
def dataset_search_check(ctx):
    """Report missing, unsupported, or inconsistent search projections."""
    _maintain_dataset_search(ctx, False)


@dataset_search_commands.command(name="rebuild")
@click.pass_context
def dataset_search_rebuild(ctx):
    """Recompute projections, retrying catalog or tag changes up to three times."""
    _maintain_dataset_search(ctx, True)


@commands.group(invoke_without_command=True)
@click.pass_obj
@click.option("--app", "-a", default=None, help="Application import path")
@click.option("--app-title", default=None, help="Title of the Kedro GraphQL application")
@click.option("--app-description", default=None, help="Description of the Kedro GraphQL application")
@click.option("--backend", default=None, help="The only supported value for this option is 'kedro_graphql.backends.mongodb.MongoBackend'")
@click.option("--broker", default=None, help="URI to broker e.g. 'redis://localhost'")
@click.option("--celery-result-backend", default=None, help="URI to backend for celery results e.g. 'redis://localhost'")
@click.option("--celery-abort-polling-interval", default=None, type=float, help="Polling interval in seconds for checking abort status while a pipeline subprocess is running")
@click.option("--celery-abort-grace-period", default=None, type=float, help="Grace period in seconds before escalating abort signals from SIGINT to SIGTERM/SIGKILL")
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
@click.option("--dataset-search-timeout-seconds", default=None, type=float, help="Maximum duration of a dataset search, including unenriched records")
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
def gql(metadata, app, app_title, app_description, backend, broker, celery_result_backend, celery_abort_polling_interval, celery_abort_grace_period, client_uri_graphql, client_uri_ws, conf_source,
        dataset_filepath_masks, dataset_filepath_allowed_roots, deprecations_docs, env, events_config, imports,
        local_file_provider_download_allowed_roots,
        local_file_provider_jwt_algorithm, local_file_provider_jwt_secret_key, local_file_provider_server_url,
        local_file_provider_upload_allowed_roots, local_file_provider_upload_max_file_size_mb,
        log_path_prefix, log_tmp_dir, dataset_search_timeout_seconds, mongo_db_collection, mongo_db_name, mongo_uri, permissions,
        permissions_group_to_role_map, permissions_role_to_action_map, project_version, root_path, runner,
        signed_url_max_expires_in_sec, signed_url_provider,
        reload, reload_path, api_spec, ui, ui_spec, worker):
    """Commands for working with kedro-graphql."""

    option_values = {
        "app": app,
        "app_title": app_title,
        "app_description": app_description,
        "backend": backend,
        "broker": broker,
        "celery_result_backend": celery_result_backend,
        "celery_abort_polling_interval": celery_abort_polling_interval,
        "celery_abort_grace_period": celery_abort_grace_period,
        "client_uri_graphql": client_uri_graphql,
        "client_uri_ws": client_uri_ws,
        "conf_source": conf_source,
        "dataset_filepath_masks": dataset_filepath_masks,
        "dataset_filepath_allowed_roots": dataset_filepath_allowed_roots,
        "deprecations_docs": deprecations_docs,
        "env": env,
        "events_config": events_config,
        "imports": imports,
        "local_file_provider_download_allowed_roots": local_file_provider_download_allowed_roots,
        "local_file_provider_jwt_algorithm": local_file_provider_jwt_algorithm,
        "local_file_provider_jwt_secret_key": local_file_provider_jwt_secret_key,
        "local_file_provider_server_url": local_file_provider_server_url,
        "local_file_provider_upload_allowed_roots": local_file_provider_upload_allowed_roots,
        "local_file_provider_upload_max_file_size_mb": local_file_provider_upload_max_file_size_mb,
        "log_path_prefix": log_path_prefix,
        "log_tmp_dir": log_tmp_dir,
        "dataset_search_timeout_seconds": dataset_search_timeout_seconds,
        "mongo_db_collection": mongo_db_collection,
        "mongo_db_name": mongo_db_name,
        "mongo_uri": mongo_uri,
        "permissions": permissions,
        "permissions_group_to_role_map": permissions_group_to_role_map,
        "permissions_role_to_action_map": permissions_role_to_action_map,
        "project_version": project_version,
        "root_path": root_path,
        "runner": runner,
        "signed_url_max_expires_in_sec": signed_url_max_expires_in_sec,
        "signed_url_provider": signed_url_provider,
        "project_name": metadata.package_name,
    }
    if option_values["project_version"] is None:
        option_values["project_version"] = getattr(
            import_module(metadata.package_name), "__version__", "None"
        )
    overrides = {
        name: value for name, value in option_values.items() if value is not None
    }
    ctx = click.get_current_context()
    try:
        config = load_config(overrides, api_spec)
    except (ValueError, TypeError) as exc:
        if ctx.invoked_subcommand:
            raise click.ClickException("Invalid configuration: check mongo_indexes and Mongo settings.") from exc
        raise
    if ctx.invoked_subcommand:
        ctx.meta["gql_config"] = config
        return
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
                        "spec": ui_spec})
        else:
            start_ui(spec=ui_spec)

    elif worker:
        if reload:
            run_process(str(reload_path), target=start_worker, args=(config, metadata.project_path))
        else:
            start_worker(config, metadata.project_path)

    else:
        if reload:
            run_process(reload_path, target=start_app, args=(config, metadata.project_path))
        else:
            start_app(config, metadata.project_path)


gql.add_command(mongo_indexes)
gql.add_command(dataset_search_commands)
