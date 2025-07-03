from fastapi import FastAPI, Depends, Request
from fastapi.openapi.utils import get_openapi
from fastapi.security import OpenIdConnect
from strawberry.fastapi import GraphQLRouter
from cloudevents.http import from_http, to_json
from starlette.middleware.sessions import SessionMiddleware

from .logs.logger import logger
from .backends import init_backend
from .celeryapp import celery_app
from .config import config
from .decorators import RESOLVER_PLUGINS, TYPE_PLUGINS, discover_plugins
from .models import PipelineTemplates
from .schema import build_schema
from .tasks import handle_event
from .auth.oidc.dependencies import protected_endpoint
from .auth.oidc import init_auth_router

# Replace with your OIDC provider's configuration
# OPENID_CONNECT_URL = "https://localhost/oidc/.well-known/openid-configuration"
# CLIENT_ID = "api"
# SCOPES = ["openid", "profile", "email", "groups"]


class KedroGraphQL(FastAPI):

    def __init__(self, kedro_session=None, config=config):
        super(KedroGraphQL, self).__init__(
            title=config["KEDRO_GRAPHQL_APP_TITLE"],
            description=config["KEDRO_GRAPHQL_APP_DESCRIPTION"],
            version=config["KEDRO_GRAPHQL_PROJECT_VERSION"],
            docs_url="/docs",  # Swagger UI URL
            openapi_tags=config["KEDRO_GRAPHQL_OPENAPI_TAGS"],  # OpenAPI tags
            openapi_url="/openapi.json",  # Serve OpenAPI schema
        )
# swagger_ui_init_oauth={  # Configure Swagger UI for OAuth
# "clientId": CLIENT_ID,
# "scopes": " ".join(SCOPES),
# "usePkceWithAuthorizationCodeGrant": True,
# },)

        self.add_middleware(
            SessionMiddleware,
            secret_key=config['KEDRO_GRAPHQL_COOKIE_SECRET']
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

        self.include_router(init_auth_router(config))

        self.celery_app = celery_app(self.config, self.backend, self.schema)

        # Initialize the OpenID Connect handler
        # oidc = OpenIdConnect(openIdConnectUrl=OPENID_CONNECT_URL)

        # Define a protected endpoint
        @self.get("/protected", tags=config["KEDRO_GRAPHQL_OPENAPI_TAGS"], dependencies=[Depends(protected_endpoint)])
        async def protected(request: Request):
            """
            A protected endpoint that requires authentication.
            The `token` parameter will be automatically populated with the
            user's ID token from the OIDC provider.
            """
            return {"message": "Protected endpoint accessed", "request": request}

# Customize OpenAPI schema for better UI experience
# def custom_openapi():
# if self.openapi_schema:
# return self.openapi_schema
# openapi_schema = get_openapi(
# title=self.title,
# version=self.version,
# description=self.description,
# routes=self.routes,
# )
# openapi_schema["components"]["securitySchemes"] = {
# "openIdConnect": {
# "type": "openIdConnect",
# "openIdConnectUrl": OPENID_CONNECT_URL,
# }
# }
# openapi_schema["security"] = [{"openIdConnect": []}]
# self.openapi_schema = openapi_schema
##
# self.openapi = custom_openapi

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
