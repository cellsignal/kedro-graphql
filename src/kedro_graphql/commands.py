import click
import uvicorn
from importlib import import_module
from .config import config
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from watchfiles import run_process
import pathlib
from .logs.logger import logger

def init_app(app, config, session):
        ## create app instance
        module, class_name = app.rsplit(".", 1)
        module = import_module(module)
        class_inst = getattr(module, class_name)
        return class_inst(kedro_session = session, config = config)
    

def start_app(app, config, conf_source, env, package_name, project_path):
    bootstrap_project(project_path) 
    with KedroSession.create(package_name, project_path = project_path, env = env, conf_source = conf_source) as session:
        a = init_app(app, config, session)
        uvicorn.run(a, host="0.0.0.0", port=5000, log_level="info")

def start_worker(app, config, conf_source, env, package_name, project_path):

    bootstrap_project(project_path) 
    with KedroSession.create(package_name, project_path = project_path, env = env, conf_source = conf_source) as session:
        a = init_app(app, config, session)
        from .celeryapp import celery_app
        capp = celery_app(a.config, a.backend)
        worker = capp.Worker()
        worker.start()


@click.group(name="kedro-graphql")
def commands():
    pass


@commands.command()
@click.pass_obj
@click.option(
    "--app",
    "-a",
    default = config["KEDRO_GRAPHQL_APP"],
    help="Application import path"
)
@click.option(
    "--backend",
    default = config["KEDRO_GRAPHQL_BACKEND"],
    help="The only supported value for this option is 'kedro_graphql.backends.mongodb.MongoBackend'"
)
@click.option(
    "--broker",
    default = config["KEDRO_GRAPHQL_BROKER"],
    help="URI to broker e.g. 'redis://localhost'"
)
@click.option(
    "--celery-result-backend",
    default = config["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"],
    help="URI to backend for celery results e.g. 'redis://localhost'"
)
@click.option(
    "--conf-source",
    default = config["KEDRO_GRAPHQL_CONF_SOURCE"],
    help="Path of a directory where project configuration is stored."
)
@click.option(
    "--env",
    "-e",
    default = config["KEDRO_GRAPHQL_ENV"],
    help="Kedro configuration environment name. Defaults to `local`."
)
@click.option(
    "--imports",
    "-i",
    default = config["KEDRO_GRAPHQL_IMPORTS"],
    help="Additional import paths"
)
@click.option(
    "--mongo-uri",
    default = config["MONGO_URI"],
    help="URI to mongodb e.g. 'mongodb://root:example@localhost:27017/'"
)
@click.option(
    "--mongo-db-name",
    default = config["MONGO_DB_NAME"],
    help="Name to use for collection in mongo e.g. 'pipelines'"
)
@click.option(
    "--runner",
    default = config["KEDRO_GRAPHQL_RUNNER"],
    help="Execution mechanism to run pipelines e.g. 'kedro.runner.SequentialRunner'"
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
    type=click.Path(exists=True, resolve_path=True, path_type = pathlib.Path),
    help="Path to watch for file changes, defaults to <project path>/src"
)
@click.option(
    "--worker",
    "-w",
    is_flag=True,
    default=False,
    help="Start a celery worker."
)

def gql(metadata, app, backend, broker, celery_result_backend, conf_source, 
        env, imports, mongo_uri, mongo_db_name, runner, reload, reload_path, worker):
    """Commands for working with kedro-graphql."""

    config.update({
            "MONGO_URI": mongo_uri,
            "MONGO_DB_NAME": mongo_db_name,
            "KEDRO_GRAPHQL_IMPORTS": imports,
            "KEDRO_GRAPHQL_APP": app,
            "KEDRO_GRAPHQL_BACKEND": backend,
            "KEDRO_GRAPHQL_BROKER": broker,
            "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": celery_result_backend,
            "KEDRO_GRAPHQL_RUNNER": runner,
            "KEDRO_GRAPHQL_ENV": env,
            "KEDRO_GRAPHQL_CONF_SOURCE": conf_source})
    
    if not reload_path:
        reload_path = metadata.project_path.joinpath("src")
    
    if reload:
        logger.info("AUTO-RELOAD ACTIVATED, watching '" + str(reload_path) + "' for changes")

    if worker:
        if reload:
            run_process(str(reload_path), target = start_worker, args = (app, config, conf_source, env, metadata.package_name, metadata.project_path))
        else:
            start_worker(app, config, conf_source, env, metadata.package_name, metadata.project_path)

    else:
        if reload:
            run_process(reload_path, target = start_app, args = (app, config, conf_source, env, metadata.package_name, metadata.project_path))
        else:
            start_app(app, config, conf_source, env, metadata.package_name, metadata.project_path)

    ##with KedroSession.create(metadata.package_name, project_path=metadata.project_path, env = env, conf_source = conf_source) as session:
    ##    ## create app instance
    ##    module, class_name = app.rsplit(".", 1)
    ##    module = import_module(module)
    ##    class_inst = getattr(module, class_name)
    ##    a = class_inst(kedro_session = session, config = config) 
  
    ##    if worker:
    ##        from .celeryapp import celery_app
    ##        capp = celery_app(a.config, a.backend)
    ##        worker = capp.Worker()
    ##        worker.start()
    ##    else:

    ##        uvicorn.run(a, host="0.0.0.0", port=5000, log_level="info")
                

