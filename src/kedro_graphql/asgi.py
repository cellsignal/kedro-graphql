from fastapi import FastAPI, Request, Depends, HTTPException, status, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import jwt
import shutil
from pathlib import Path
from strawberry.fastapi import GraphQLRouter
from cloudevents.http import from_http, to_json
from cloudevents.pydantic.v1 import CloudEvent
from contextlib import asynccontextmanager

from .logs.logger import logger
from .backends import init_backend
from .celeryapp import celery_app
from .decorators import RESOLVER_PLUGINS, TYPE_PLUGINS, discover_plugins
from .models import PipelineTemplates
from .schema import build_schema
from .config import load_config
from .permissions import get_permissions
from starlette.requests import Request
from kedro_graphql.utils import build_graphql_query
from kedro_graphql.models import PipelineInput, Pipeline, ParameterInput

CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.backend.startup()
    yield
    app.backend.shutdown()


class KedroGraphQL(FastAPI):

    def __init__(self, kedro_session=None, config=CONFIG):
        super(KedroGraphQL, self).__init__(
            title=config["KEDRO_GRAPHQL_APP_TITLE"],
            description=config["KEDRO_GRAPHQL_APP_DESCRIPTION"],
            version=config["KEDRO_GRAPHQL_PROJECT_VERSION"],
            docs_url="/docs",  # Swagger UI URL
            root_path=config["KEDRO_GRAPHQL_ROOT_PATH"],
            lifespan=lifespan
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

        class Info:
            """A simple class to hold the request context for permissions."""

            def __init__(self, request: Request):
                self.context = {"request": request}

        @staticmethod
        def authenticate_factory(action: str = None):
            """Factory function to create an authentication dependency.

            Kwargs:
                action (str): The action for which the user needs to be authenticated.
            Returns:
                function: A function that checks if the user is authenticated.
            """

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

                access = PERMISSIONS_CLASS(action=action).has_permission(
                    None, Info(request))
                if not access:
                    raise HTTPException(detail="User is not authenticated",
                                        status_code=status.HTTP_403_FORBIDDEN)
                else:
                    return access
            return authenticate

        if isinstance(self.config.get("KEDRO_GRAPHQL_EVENTS_CONFIG", None), dict):

            @self.post(
                "/event/",
                dependencies=[Depends(authenticate_factory(action="create_event"))],
            )
            async def event(request: Request):
                """
                Endpoint to handle cloudevents.

                Args:
                request (Request): The incoming request containing the CloudEvent.
                Returns:
                dict: Result id of the event handling.
                """
                econf = self.config["KEDRO_GRAPHQL_EVENTS_CONFIG"]

                body = await request.body()
                event: CloudEvent = from_http(
                    request.headers, body
                )  # will raise if not a valid cloudevent

                logger.info(f"Received event: {to_json(event)}")

                # match event details to corresponding pipelines
                source = event.get_attributes().get("source", None)
                type = event.get_attributes().get("type", None)

                pipeline_names = [
                    k
                    for k, v in econf.items()
                    if v["source"] == source and v["type"] == type
                ]

                created_pipelines = []

                for n in pipeline_names:

                    pipeline_input = PipelineInput.from_event(
                        name=n, event=event, state="READY"
                    )

                    q_create = build_graphql_query(
                        "createPipelineReturnFull", fragments=["FullPipeline"]
                    )

                    # Need to STAGE to get a pipeline id to pass as parameter
                    resp = await self.schema.execute(
                        q_create,
                        variable_values={
                            "pipeline": pipeline_input.encode(encoder="graphql")
                        },
                        context_value={"request": request},
                    )

                    staged = Pipeline.decode(
                        resp.data["createPipeline"], decoder="graphql"
                    )

                    pipeline_input.state = "READY"

                    pipeline_input.parameters.append(
                        ParameterInput(name="id", value=str(staged.id), type="STRING")
                    )

                    q_update = build_graphql_query(
                        "updatePipelineReturnFull", fragments=["FullPipeline"]
                    )

                    resp = await self.schema.execute(
                        q_update,
                        variable_values={
                            "id": staged.id,
                            "pipeline": pipeline_input.encode(encoder="graphql"),
                        },
                        context_value={"request": request},
                    )

                    created = Pipeline.decode(
                        resp.data["updatePipeline"], decoder="graphql"
                    )
                    created_pipelines.append(created.encode(encoder="dict"))

                    logger.info(
                        f"event " f"{event.get('id')} triggered pipeline {created.id}")

                return created_pipelines

        else:
            logger.warning(
                "KEDRO_GRAPHQL_EVENTS_CONFIG is not set or not a dictionary. "
                "Event handling endpoint will not be available."
            )

        @self.get("/download", dependencies=[Depends(authenticate_factory(action="read_dataset"))])
        def download(token: str):
            """
            Endpoint to download a file.

            Args:
                token (str): The JWT token for authentication.

            Returns:
                FileResponse: The file to download.
            """
            try:
                payload = jwt.decode(
                    token,
                    self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                    algorithms=[
                        self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]]
                )
                path = Path(payload["filepath"])
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=403, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=403, detail="Invalid token")

            ALLOWED_ROOTS = []

            for root in self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS"]:
                ALLOWED_ROOTS.append(Path(root).resolve())
                # print(f"Allowed root: {Path(root).resolve()}")

            if not any(path.is_relative_to(root) for root in ALLOWED_ROOTS):
                raise HTTPException(
                    status_code=403,
                    detail=f"Path {path} is not allowed. Allowed roots: {ALLOWED_ROOTS}"
                )

            if not path.exists() or not path.is_file():
                raise HTTPException(status_code=404, detail="File not found")

            return FileResponse(
                path,
                headers={"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0",
                         "Access-Control-Allow-Origin": "*"})

        @self.post("/upload", dependencies=[Depends(authenticate_factory(action="create_dataset"))])
        async def upload(token: str = Form(...), file: UploadFile = File(...)):
            """
            Endpoint to upload a file.

            Args:
                token (str): The JWT token for authentication.
                file (UploadFile): The file to upload.

            Returns:
                dict: A success message and the file path.
            """

            if file.size > self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB"] * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds the maximum limit of {self.config['KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB']} MB"
                )

            try:
                payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                                     algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])
                path = Path(payload["filepath"]).resolve()
                # print(f"Destination path: {path}")
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=403, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=403, detail="Invalid token")

            ALLOWED_ROOTS = []

            for root in self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS"]:
                ALLOWED_ROOTS.append(Path(root).resolve())
                # print(f"Allowed root: {Path(root).resolve()}")

            if not any(path.is_relative_to(root) for root in ALLOWED_ROOTS):
                raise HTTPException(
                    status_code=403,
                    detail=f"Path {path} is not allowed. Allowed roots: {ALLOWED_ROOTS}"
                )

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "wb") as out_file:
                    shutil.copyfileobj(file.file, out_file)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

            return {"status": "success", "path": str(path)}
