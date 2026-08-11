from strawberry.fastapi import BaseContext
from starlette.requests import Request
from starlette.websockets import WebSocket


class GraphQLContext(BaseContext):
    def __init__(self, request: Request | WebSocket | None = None):
        super().__init__()
        self.request = request
