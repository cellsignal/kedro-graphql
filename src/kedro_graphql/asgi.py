import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

import jwt
import strawberry
from celery import Celery
from cloudevents.http import from_http, to_json
from cloudevents.pydantic.v1 import CloudEvent
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from strawberry.fastapi import GraphQLRouter
from strawberry.permission import BasePermission

from .backends import init_backend
from .backends.base import BaseBackend
from .celeryapp import celery_app
from .config import KedroGraphQLConfig
from .context import GraphQLContext
from .decorators import TYPE_PLUGINS, discover_plugins
from .hooks import available_hook_names, hook_manager_for
from .logs.logger import logger
from .models import ParameterInput, Pipeline, PipelineInput
from .permissions import get_permissions
from .project import ProjectMetadata
from .schema import build_schema
from .signed_url.base import SignedUrlProvider
from .utils import build_graphql_query


@dataclass(frozen=True)
class AppServices:
    config: KedroGraphQLConfig
    metadata: ProjectMetadata
    backend: BaseBackend
    celery: Celery
    schema: strawberry.Schema
    permission_class: type[BasePermission]
    signed_url_provider: type[SignedUrlProvider]
    available_hooks: set[str]


def create_app(config: KedroGraphQLConfig, metadata: ProjectMetadata) -> FastAPI:
    """Build the web application from validated configuration and project metadata."""

    hooks = available_hook_names()
    unknown_hooks = sorted(set(config.always_hooks) - hooks)
    if unknown_hooks:
        raise ValueError(f"Unavailable always hooks: {unknown_hooks}")
    hook_manager_for(config.always_hooks)

    discover_plugins(config)
    schema = build_schema(TYPE_PLUGINS)
    backend = init_backend(config)
    celery = celery_app(config, backend)
    permission_class = get_permissions(config.permissions)
    module_name, provider_name = config.signed_url_provider.rsplit(".", 1)
    signed_url_provider = getattr(import_module(module_name), provider_name)
    if not issubclass(signed_url_provider, SignedUrlProvider):
        raise TypeError(f"{provider_name} must inherit from SignedUrlProvider")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await backend.startup()
        yield
        await backend.shutdown()

    app = FastAPI(
        title=config.app_title,
        description=config.app_description,
        version=config.project_version,
        docs_url="/docs",
        root_path=config.root_path,
        lifespan=lifespan,
    )
    app.state.services = AppServices(
        config,
        metadata,
        backend,
        celery,
        schema,
        permission_class,
        signed_url_provider,
        hooks,
    )

    def get_context() -> GraphQLContext:
        return GraphQLContext()

    graphql_app = GraphQLRouter(schema, context_getter=get_context)
    app.include_router(graphql_app, prefix="/graphql")

    class Info:
        def __init__(self, request: Request):
            self.context = GraphQLContext(request)

    def authenticate(action: str):
        def dependency(request: Request):
            if not permission_class(action=action).has_permission(None, Info(request)):
                raise HTTPException(
                    detail="User is not authenticated",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            return True

        return dependency

    if config.events_config:

        @app.post(
            "/event/", dependencies=[Depends(authenticate("create_event"))]
        )
        async def event(request: Request):
            body = await request.body()
            event: CloudEvent = from_http(request.headers, body)
            logger.info("Received event: %s", to_json(event))
            source = event.get_attributes().get("source")
            event_type = event.get_attributes().get("type")
            names = [
                name
                for name, event_config in config.events_config.items()
                if event_config["source"] == source
                and event_config["type"] == event_type
            ]
            created_pipelines = []
            for name in names:
                pipeline_input = PipelineInput.from_event(
                    name=name, event=event, state="STAGED"
                )
                response = await schema.execute(
                    build_graphql_query(
                        "createPipelineReturnFull", fragments=["FullPipeline"]
                    ),
                    variable_values={
                        "pipeline": pipeline_input.encode(encoder="graphql")
                    },
                    context_value=GraphQLContext(request),
                )
                staged = Pipeline.decode(response.data["createPipeline"])
                pipeline_input.state = "READY"
                pipeline_input.parameters.append(
                    ParameterInput(
                        name="id", value=str(staged.id), type="STRING"
                    )
                )
                response = await schema.execute(
                    build_graphql_query(
                        "updatePipelineReturnFull", fragments=["FullPipeline"]
                    ),
                    variable_values={
                        "id": staged.id,
                        "pipeline": pipeline_input.encode(encoder="graphql"),
                    },
                    context_value=GraphQLContext(request),
                )
                created = Pipeline.decode(response.data["updatePipeline"])
                created_pipelines.append(created.encode(encoder="dict"))
            return created_pipelines

    @app.get(
        "/download", dependencies=[Depends(authenticate("read_dataset"))]
    )
    def download(token: str):
        try:
            payload = jwt.decode(
                token,
                config.local_file_provider_jwt_secret_key,
                algorithms=[config.local_file_provider_jwt_algorithm],
            )
            path = Path(payload["filepath"]).resolve()
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=403, detail="Invalid token")
        roots = [
            Path(root).resolve()
            for root in config.local_file_provider_download_allowed_roots
        ]
        if not any(path.is_relative_to(root) for root in roots):
            raise HTTPException(status_code=403, detail=f"Path {path} is not allowed")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            path,
            headers={
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Expires": "0",
                "Access-Control-Allow-Origin": "*",
            },
        )

    @app.post(
        "/upload", dependencies=[Depends(authenticate("create_dataset"))]
    )
    async def upload(token: str = Form(...), file: UploadFile = File(...)):
        if (
            file.size is not None
            and file.size
            > config.local_file_provider_upload_max_file_size_mb * 1024 * 1024
        ):
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit")
        try:
            payload = jwt.decode(
                token,
                config.local_file_provider_jwt_secret_key,
                algorithms=[config.local_file_provider_jwt_algorithm],
            )
            path = Path(payload["filepath"]).resolve()
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=403, detail="Invalid token")
        roots = [
            Path(root).resolve()
            for root in config.local_file_provider_upload_allowed_roots
        ]
        if not any(path.is_relative_to(root) for root in roots):
            raise HTTPException(status_code=403, detail=f"Path {path} is not allowed")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as output:
                shutil.copyfileobj(file.file, output)
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"Upload failed: {error}")
        return {"status": "success", "path": str(path)}

    return app
