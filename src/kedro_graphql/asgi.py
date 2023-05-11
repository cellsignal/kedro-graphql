from fastapi import FastAPI
from strawberry.asgi import GraphQL
from .config import config, backend, backend_kwargs
#, RESOLVER_PLUGINS
from .schema import schema
from celery.result import AsyncResult



graphql_app = GraphQL(schema)
app = FastAPI()
app.config = config
#app.resolver_plugins = RESOLVER_PLUGINS
app.backend = backend(**backend_kwargs)

@app.on_event("startup")
def startup_backend():
    app.backend.startup()

@app.on_event("shutdown")
def shutdown_backend():
    app.backend.shutdown()


app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

