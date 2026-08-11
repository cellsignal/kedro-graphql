from fastapi.middleware.cors import CORSMiddleware

from kedro_graphql.asgi import create_app as create_default_app
from kedro_graphql.config import KedroGraphQLConfig
from kedro_graphql.project import ProjectMetadata


def create_app(config: KedroGraphQLConfig, metadata: ProjectMetadata):
    app = create_default_app(config, metadata)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app
