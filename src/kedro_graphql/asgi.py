from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from .backends import init_backend
from .schema import build_schema       
class KedroGraphql(FastAPI):
    def __init__(self):
        super(KedroGraphql, self).__init__()

        self.backend = init_backend()
    
        @self.on_event("startup")
        def startup_backend():
            self.backend.startup()
    
        @self.on_event("shutdown")
        def shutdown_backend():
            self.backend.shutdown()
    
        graphql_app = GraphQLRouter(build_schema())
        self.include_router(graphql_app, prefix = "/graphql")
        self.add_websocket_route("/graphql", graphql_app)

