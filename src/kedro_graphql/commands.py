import click
import uvicorn
import os
from .config import config
from importlib import import_module

@click.group(name="kedro-graphql")
def commands():
    pass


@commands.command()
@click.pass_obj
@click.option(
    "--app",
    "-a",
    default=config["KEDRO_GRAPHQL_APP"],
    help="Application import path"
)
@click.option(
    "--imports",
    "-i",
    default=config["KEDRO_GRAPHQL_IMPORTS"],
    help="Additional import paths"
)
@click.option(
    "--worker",
    "-w",
    is_flag=True,
    default=False,
    help="Start a celery worker."
)
def gql(metadata, app, imports, worker):
    """Commands for working with kedro-graphql."""
    if worker:
        from .celeryapp import app
        worker = app.Worker()
        worker.start()
    else:
        module, class_name = app.rsplit(".", 1)
        module = import_module(module)
        class_inst = getattr(module, class_name)

        imports = [i.strip() for i in imports.split(",") if len(i.strip()) > 0]
        for i in imports:
            import_module(i)
        
        uvicorn.run(class_inst(), port=5000, log_level="info")
