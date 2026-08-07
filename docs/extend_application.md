# Extend the application

The configured application is a factory that receives validated configuration and
the Kedro project metadata snapshot. A custom factory can add normal FastAPI routes
or middleware to the default application.

```python
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
```

Select it with the CLI:

```bash
kedro gql --app "my_kedro_project.app.create_app"
```

The factory signature is `create_app(config: KedroGraphQLConfig, metadata:
ProjectMetadata) -> FastAPI`. Pipeline execution sessions are created by workers;
the web application does not own a `KedroSession`.
