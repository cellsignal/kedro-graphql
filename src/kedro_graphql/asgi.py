from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from .backends import init_backend
from .celeryapp import celery_app
from .config import config
from .decorators import RESOLVER_PLUGINS, TYPE_PLUGINS, discover_plugins
from .models import PipelineTemplates
from .schema import build_schema
from .tasks import handle_event
from fastapi import Request
from cloudevents.http import from_http, to_json
from .logs.logger import logger


class KedroGraphQL(FastAPI):

    def __init__(self, kedro_session=None, config=config):
        super(KedroGraphQL, self).__init__()

        self.kedro_session = kedro_session
        self.kedro_context = self.kedro_session.load_context()
        self.kedro_catalog = self.kedro_context.config_loader["catalog"]
        self.kedro_parameters = self.kedro_context.config_loader["parameters"]
        from kedro.framework.project import pipelines
        self.kedro_pipelines = pipelines
        self.kedro_pipelines_index = PipelineTemplates._build_pipeline_index(
            self.kedro_pipelines, self.kedro_catalog, self.kedro_parameters)

        self.config = config

        self.resolver_plugins = RESOLVER_PLUGINS
        self.type_plugins = TYPE_PLUGINS

        discover_plugins(self.config)
        self.schema = build_schema(self.type_plugins)
        self.backend = init_backend(self.config)
        self.graphql_app = GraphQLRouter(self.schema)
        self.include_router(self.graphql_app, prefix="/graphql")
        self.add_websocket_route("/graphql", self.graphql_app)
        self.celery_app = celery_app(self.config, self.backend, self.schema)

        @self.on_event("startup")
        def startup_backend():
            self.backend.startup()

        @self.on_event("shutdown")
        def shutdown_backend():
            self.backend.shutdown()

        if self.config.get("KEDRO_GRAPHQL_EVENTS_CONFIG", None) and isinstance(self.config["KEDRO_GRAPHQL_EVENTS_CONFIG"], dict):
            @self.post("/event/")
            async def event(request: Request):
                """
                Endpoint to handle cloudevents.

                Args:
                request (Request): The incoming request containing the CloudEvent.
                Returns:
                dict: Result id of the event handling.
                """
                body = await request.body()
                event = from_http(request.headers, body)
                logger.info(f"Received event: {event}")
                result = handle_event.delay(
                    to_json(event), config["KEDRO_GRAPHQL_EVENTS_CONFIG"])
                return {"result": result.task_id}
        else:
            logger.warning(
                "KEDRO_GRAPHQL_EVENTS_CONFIG is not set or not a dictionary. "
                "Event handling endpoint will not be available."
            )
