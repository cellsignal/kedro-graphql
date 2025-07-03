import typing
import strawberry
from starlette.requests import Request
from starlette.websockets import WebSocket
from strawberry.permission import BasePermission
from .logs.logger import logger
from .config import config


def get_permissions(permissions_cls) -> BasePermission:
    module_path, class_name = permissions_cls.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    module_class = getattr(module, class_name)
    logger.info("using permission class: " +
                str(module_class))

    return module_class


class IsAuthenticatedAlways(BasePermission):
    message = "User is not authenticated"
    error_extensions = {"code": "UNAUTHORIZED"}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:

        return True


class IsAuthenticatedXForwardedEmail(BasePermission):
    message = "User is not authenticated"
    error_extensions = {"code": "UNAUTHORIZED"}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:

        request: typing.Union[Request, WebSocket] = info.context["request"]
        print("requested source: ", info.context["request"].__dict__)
        if request.headers.get("X-Forwarded-Email", None):
            return True
        return False


class IsAuthenticatedXForwardedEmailAndGroups(BasePermission):
    message = "User is not authenticated"
    error_extensions = {"code": "UNAUTHORIZED"}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:

        request: typing.Union[Request, WebSocket] = info.context["request"]

        if request.headers.get("X-Forwarded-Email", None) and request.headers.get("X-Forwarded-Groups", None):
            return True
        return False


class IsAuthenticatedXForwardedRBAC(BasePermission):
    message = "User is not authenticated"
    error_extensions = {"code": "UNAUTHORIZED"}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:

        built_in_actions = ["create_pipeline",
                            "read_pipeline",
                            "update_pipeline",
                            "delete_pipeline",
                            "create_dataset",
                            "read_dataset"]

        request: typing.Union[Request, WebSocket] = info.context["request"]

        if request.headers.get("X-Forwarded-Email", None) and request.headers.get("X-Forwarded-Groups", None):
            return True
        return False
