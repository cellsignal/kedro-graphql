from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from .config import config, backend, backend_kwargs
from .schema import schema
from celery.result import AsyncResult


class KedroGraphql(FastAPI):
    def __init__(self):
        super(KedroGraphql, self).__init__()
        graphql_app = GraphQLRouter(schema)
        self.config = config
        self.backend = backend(**backend_kwargs)
    
        @self.on_event("startup")
        def startup_backend():
            self.backend.startup()
    
        @self.on_event("shutdown")
        def shutdown_backend():
            self.backend.shutdown()
    
    
        self.include_router(graphql_app, prefix = "/graphql")
        self.add_websocket_route("/graphql", graphql_app)
