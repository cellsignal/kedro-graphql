import click
import uvicorn

@click.group(name="kedro-graphql")
def commands():
    pass


@commands.command()
@click.pass_obj
@click.option(
    "--worker",
    "-w",
    is_flag=True,
    default=False,
    help="Start a celery worker."
)
def gql(metadata, worker):
    """Commands for working with kedro-graphql."""

    if worker:
        from .celeryapp import app
        worker = app.Worker()
        worker.start()
    else:
        from .asgi import app
        uvicorn.run(app, port=5000, log_level="info")
