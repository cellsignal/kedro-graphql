
from dotenv import dotenv_values
import os


config = {
            "MONGO_URI": "mongodb://root:example@localhost:27017/",
            "MONGO_DB_NAME": "pipelines",
            "KEDRO_GRAPHQL_IMPORTS": "kedro_graphql.plugins.plugins,",
            "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphQL",
            "KEDRO_GRAPHQL_BACKEND": "kedro_graphql.backends.mongodb.MongoBackend",
            "KEDRO_GRAPHQL_BROKER": "redis://localhost",
            "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": "redis://localhost",
            "KEDRO_GRAPHQL_RUNNER": "kedro.runner.SequentialRunner",
            "KEDRO_GRAPHQL_ENV": "local",
            "KEDRO_GRAPHQL_CONF_SOURCE": None,
            "KEDRO_GRAPHQL_DEPRECATIONS_DOCS": "https://github.com/opensean/kedro-graphql/blob/main/README.md#deprecations",
            #"KEDRO_GRAPHQL_RUNNER": "kedro_graphql.runner.argo.ArgoWorkflowsRunner",
            }

config = {
        **config,
        **dotenv_values(".env"),  # load 
        **os.environ,  # override loaded values with environment variables
    }
