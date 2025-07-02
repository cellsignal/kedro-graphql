from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import jwt
import shutil
from pathlib import Path
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

        @self.get("/download")
        def download_file(token: str):
            try:
                payload = jwt.decode(
                    token,
                    self.config["KEDRO_GRAPHQL_JWT_SECRET_KEY"],
                    algorithms=[self.config["KEDRO_GRAPHQL_JWT_ALGORITHM"]]
                )
                filepath = Path(payload["filepath"])
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=403, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=403, detail="Invalid token")

            if not filepath.exists() or not filepath.is_file():
                raise HTTPException(status_code=404, detail="File not found")

            return FileResponse(filepath, headers={"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0"})

        @self.post("/upload")
        async def upload_file(token: str = Form(...), file: UploadFile = File(...)):
            try:
                payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_JWT_SECRET_KEY"],
                                     algorithms=[self.config["KEDRO_GRAPHQL_JWT_ALGORITHM"]])
                dest_path = Path(payload["filepath"]).resolve()
                print(f"Destination path: {dest_path}")
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=403, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=403, detail="Invalid token")

            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as out_file:
                    shutil.copyfileobj(file.file, out_file)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

            return {"status": "success", "path": str(dest_path)}
