from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
import os
#from .backends import init_backend
#from .schema import build_schema       
from .decorators import TYPE_PLUGINS, RESOLVER_PLUGINS, discover_plugins
from .backends import init_backend
from .models import PipelineTemplate
from .schema import build_schema
from .celeryapp import celery_app
from .config import config
from .models import PipelineTemplates





class KedroGraphQL(FastAPI):

    ##def __init__(self, gql_conf = {}, package_name = None, project_path = None,
    ##             conf_source = None, env = None):
    def __init__(self, kedro_session = None, config = config):
        super(KedroGraphQL, self).__init__()

        self.kedro_session = kedro_session
        self.kedro_context = self.kedro_session.load_context()
        self.kedro_catalog = self.kedro_context.config_loader["catalog"]
        self.kedro_parameters = self.kedro_context.config_loader["parameters"]
        from kedro.framework.project import pipelines
        self.kedro_pipelines = pipelines
        self.kedro_pipelines_index = PipelineTemplates._build_pipeline_index(self.kedro_pipelines, self.kedro_catalog, self.kedro_parameters)


        self.config = config

        self.resolver_plugins = RESOLVER_PLUGINS
        self.type_plugins = TYPE_PLUGINS

        discover_plugins(self.config)
        self.schema = build_schema(self.type_plugins)
        self.backend = init_backend(self.config)
        self.graphql_app = GraphQLRouter(self.schema)
        self.include_router(self.graphql_app, prefix = "/graphql")
        self.add_websocket_route("/graphql", self.graphql_app)
        self.celery_app = celery_app(self.config, self.backend)

        @self.on_event("startup")
        def startup_backend():
            self.backend.startup()
    
        @self.on_event("shutdown")
        def shutdown_backend():
            self.backend.shutdown()