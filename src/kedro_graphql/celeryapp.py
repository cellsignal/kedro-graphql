from celery import Celery

app = Celery('kedro_graphql', backend='redis://localhost', broker='redis://localhost')

app.config_from_object('kedro_graphql.celeryconfig')
