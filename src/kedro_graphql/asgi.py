from fastapi import FastAPI, Request, Depends, HTTPException, status
from strawberry.fastapi import GraphQLRouter
from cloudevents.http import from_http, to_json

from .logs.logger import logger
from .backends import init_backend
from .celeryapp import celery_app
from .decorators import RESOLVER_PLUGINS, TYPE_PLUGINS, discover_plugins
from .models import PipelineTemplates
from .schema import build_schema
from .tasks import handle_event
from .config import load_config
from .permissions import get_permissions
from starlette.requests import Request

CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))


class KedroGraphQL(FastAPI):

    def __init__(self, kedro_session=None, config=CONFIG):
        super(KedroGraphQL, self).__init__(
            title=config["KEDRO_GRAPHQL_APP_TITLE"],
            description=config["KEDRO_GRAPHQL_APP_DESCRIPTION"],
            version=config["KEDRO_GRAPHQL_PROJECT_VERSION"],
            docs_url="/docs",  # Swagger UI URL
        )

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

        class Info:
            """A simple class to hold the request context for permissions."""

            def __init__(self, request: Request):
                self.context = {"request": request}

        @staticmethod
        def authenticate(request: Request):
            """Dependency to authenticate the user based on permissions.
            This function checks if the user is authenticated by verifying
            the permissions class. If the user is not authenticated, it raises
            an HTTPException with a 403 Forbidden status code.
            This function is used as a dependency in the event endpoint to ensure
            that only authenticated users can create events.

            Args:
                request (Request): The incoming request.
            Returns:
                bool: True if the user is authenticated, False otherwise.
            Raises:
                HTTPException: If the user is not authenticated.
            """

            access = PERMISSIONS_CLASS(action="create_event").has_permission(
                None, Info(request))
            if not access:
                raise HTTPException(detail="User is not authenticated",
                                    status_code=status.HTTP_403_FORBIDDEN)
            else:
                return access

        if self.config.get("KEDRO_GRAPHQL_EVENTS_CONFIG", None) and isinstance(self.config["KEDRO_GRAPHQL_EVENTS_CONFIG"], dict):

            @self.post("/event/", dependencies=[Depends(authenticate)])
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
                    to_json(event), self.config["KEDRO_GRAPHQL_EVENTS_CONFIG"])
                return {"id": result.task_id}
        else:
            logger.warning(
                "KEDRO_GRAPHQL_EVENTS_CONFIG is not set or not a dictionary. "
                "Event handling endpoint will not be available."
            )
