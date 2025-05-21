import os
import pathlib
import tempfile

from dotenv import dotenv_values

config = {
    "MONGO_URI": "mongodb://root:example@localhost:27017/",
    "MONGO_DB_NAME": "pipelines",
    "KEDRO_GRAPHQL_IMPORTS": "kedro_graphql.plugins.plugins,",
    "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphQL",
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
    "KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL": "http://localhost:5000/graphql",
    "KEDRO_GRAPHQL_CLIENT_URI_WS": "ws://localhost:5000/graphql",
    "KEDRO_GRAPHQL_UI_BASEPATH": "/",
    "KEDRO_GRAPHQL_UI_TITLE": "kedro-graphql UI demo",
    "KEDRO_GRAPHQL_UI_COMPONENT_MAP": {
        "dashboard": {"sidebar": False, "component": "kedro_graphql.ui.components.pipeline_dashboard_factory.PipelineDashboardFactory", "params": ["client", "pipeline", "viz_static"]},
        "pipelines": {"sidebar": True, "component": "kedro_graphql.ui.components.pipeline_cards.PipelineCards", "params": []},
        "form": {"sidebar": False, "component": "kedro_graphql.ui.components.pipeline_form_factory.PipelineFormFactory", "params": ["component", "client", "pipeline"]},
        "search": {"sidebar": True, "component": "kedro_graphql.ui.components.pipeline_search.PipelineSearch", "params": ["client"]},
        "explore": {"sidebar": False, "component": "kedro_graphql.ui.components.pipeline_viz.PipelineViz", "params": ["viz_static, pipeline"]},
    },
}

config = {
    **config,
    **dotenv_values(".env"),  # load
    **os.environ,  # override loaded values with environment variables
}
