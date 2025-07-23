import os
import pathlib
from importlib import import_module

import click
import uvicorn
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from watchfiles import run_process

from .config import defaults, load_config
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
@click.option(
    "--app",
    "-a",
    default=None,
    help="Application import path"
)
@click.option(
    "--backend",
    default=defaults["KEDRO_GRAPHQL_BACKEND"],
    help="The only supported value for this option is 'kedro_graphql.backends.mongodb.MongoBackend'"
)
@click.option(
    "--broker",
    default=defaults["KEDRO_GRAPHQL_BROKER"],
    help="URI to broker e.g. 'redis://localhost'"
)
@click.option(
    "--celery-result-backend",
    default=defaults["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"],
    help="URI to backend for celery results e.g. 'redis://localhost'"
)
@click.option(
    "--conf-source",
    default=defaults["KEDRO_GRAPHQL_CONF_SOURCE"],
    help="Path of a directory where project configuration is stored."
)
@click.option(
    "--env",
    "-e",
    default=defaults["KEDRO_GRAPHQL_ENV"],
    help="Kedro configuration environment name. Defaults to `local`."
)
@click.option(
    "--imports",
    "-i",
    default=None,
    help="Additional import paths"
)
@click.option(
    "--mongo-uri",
    default=defaults["KEDRO_GRAPHQL_MONGO_URI"],
    help="URI to mongodb e.g. 'mongodb://root:example@localhost:27017/'"
)
@click.option(
    "--mongo-db-name",
    default=defaults["KEDRO_GRAPHQL_MONGO_DB_NAME"],
    help="Name to use for collection in mongo e.g. 'pipelines'"
)
@click.option(
    "--runner",
    default=defaults["KEDRO_GRAPHQL_RUNNER"],
    help="Execution mechanism to run pipelines e.g. 'kedro.runner.SequentialRunner'"
)
@click.option(
    "--log-tmp-dir",
    default=defaults["KEDRO_GRAPHQL_LOG_TMP_DIR"],
    help="Temporary directory for logs"
)
@click.option(
    "--log-path-prefix",
    default=defaults["KEDRO_GRAPHQL_LOG_PATH_PREFIX"],
    help="Prefix of path to save logs"
)
@click.option(
    "--reload",
    "-r",
    is_flag=True,
    default=False,
    help="Enable auto-reload."
)
@click.option(
    "--reload-path",
    default=None,
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    help="Path to watch for file changes, defaults to <project path>/src"
)
@click.option(
    "--api-spec",
    default=None,
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    help="Path to watch for file changes, defaults to <project path>/src"
)
@click.option(
    "--ui",
    "-u",
    is_flag=True,
    default=False,
    help="Start a viz app."
)
@click.option(
    "--ui-spec",
    default="",
    help="UI YAML specification file"
)
@click.option(
    "--worker",
    "-w",
    is_flag=True,
    default=False,
    help="Start a celery worker."
)
def gql(metadata, app, backend, broker, celery_result_backend, conf_source,
        env, imports, mongo_uri, mongo_db_name, runner, log_tmp_dir,
        log_path_prefix, reload, reload_path, api_spec, ui, ui_spec,
        worker):
    """Commands for working with kedro-graphql."""

    if api_spec:
        os.environ["KEDRO_GRAPHQL_API_SPEC"] = str(api_spec)
    if mongo_uri:
        os.environ["KEDRO_GRAPHQL_MONGO_URI"] = mongo_uri
    if mongo_db_name:
        os.environ["KEDRO_GRAPHQL_MONGO_DB_NAME"] = mongo_db_name
    if imports:
        os.environ["KEDRO_GRAPHQL_IMPORTS"] = imports
    if app:
        os.environ["KEDRO_GRAPHQL_APP"] = app
    if backend:
        os.environ["KEDRO_GRAPHQL_BACKEND"] = backend
    if broker:
        os.environ["KEDRO_GRAPHQL_BROKER"] = broker
    if celery_result_backend:
        os.environ["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"] = celery_result_backend
    if conf_source:
        os.environ["KEDRO_GRAPHQL_CONF_SOURCE"] = conf_source
    if env:
        os.environ["KEDRO_GRAPHQL_ENV"] = env
    if runner:
        os.environ["KEDRO_GRAPHQL_RUNNER"] = runner
    if log_tmp_dir:
        os.environ["KEDRO_GRAPHQL_LOG_TMP_DIR"] = log_tmp_dir
    if log_path_prefix:
        os.environ["KEDRO_GRAPHQL_LOG_PATH_PREFIX"] = log_path_prefix

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
                config["KEDRO_GRAPHQL_APP"], config, conf_source, env, metadata.package_name, metadata.project_path))
        else:
            start_worker(config["KEDRO_GRAPHQL_APP"], config, conf_source, env,
                         metadata.package_name, metadata.project_path)

    else:
        if reload:
            run_process(reload_path, target=start_app, args=(config["KEDRO_GRAPHQL_APP"], config, conf_source,
                        env, metadata.package_name, metadata.project_path))
        else:
            start_app(config["KEDRO_GRAPHQL_APP"], config, conf_source, env,
                      metadata.package_name, metadata.project_path)
