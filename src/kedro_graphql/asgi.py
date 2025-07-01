from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
from fastapi import Query, Response
from strawberry.fastapi import GraphQLRouter

from .backends import init_backend
from .celeryapp import celery_app
from .config import config
from .decorators import RESOLVER_PLUGINS, TYPE_PLUGINS, discover_plugins
from .models import PipelineTemplates
from .schema import build_schema


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
        self.celery_app = celery_app(self.config, self.backend)

        @self.on_event("startup")
        def startup_backend():
            self.backend.startup()

        @self.on_event("shutdown")
        def shutdown_backend():
            self.backend.shutdown()

        # Storing presigned urls in-memory token store for now
        self.presigned_urls = {}

        @self.get("/download/{filepath:path}")
        def download_file(filepath: str, token: str = Query(..., description="Token for presigned URL"),
                          Expires: int = Query(..., description="Expiration timestamp")):

            presigned_url = self.presigned_urls.get(token, None)

            if not presigned_url:
                raise HTTPException(status_code=404, detail="Token not found or expired")

            (filepath, expiration) = presigned_url

            if Expires != expiration:
                raise HTTPException(status_code=403, detail="Access Denied: Invalid expiration timestamp")

            print(f"Attempting to download file: {filepath} with token: {token} and expiration: {expiration}")
            if int(datetime.now().timestamp()) > expiration:
                del self.presigned_urls[token]
                raise HTTPException(status_code=410, detail="Token expired")

            return FileResponse(filepath, headers={"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0"})
