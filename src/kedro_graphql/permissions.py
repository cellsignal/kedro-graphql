import typing
import strawberry
from starlette.requests import Request
from starlette.websockets import WebSocket
from strawberry.permission import BasePermission
from .logs.logger import logger


def get_permissions(permissions_cls) -> BasePermission:
    module_path, class_name = permissions_cls.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    module_class = getattr(module, class_name)
    return module_class


class IsAuthenticatedAction(BasePermission):
    message = "User is not authenticated"
    error_extensions = {"code": "UNAUTHORIZED"}

    def __init__(self, action):
        self._all_actions = ["read_pipeline_template",
                             "create_pipeline",
                             "read_pipeline",
                             "update_pipeline",
                             "delete_pipeline",
                             "create_dataset",
                             "read_dataset",
                             "subscribe_to_events",
                             "subscribe_to_logs"]
        self.action = action

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:

        raise NotImplementedError


class IsAuthenticatedAlways(IsAuthenticatedAction):

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        logger.info("action: {a} source: {s}".format(a=str(self.action), s=str(source)))
        return True


class IsAuthenticatedXForwardedEmail(IsAuthenticatedAction):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        request: typing.Union[Request, WebSocket] = info.context["request"]
        if request.headers.get("X-Forwarded-Email", None):
            logger.info("permission granted - user: {u} action: {a} source: {s}".format(
                u=str(request.headers.get("X-Forwarded-Email",
                      request.headers.get("X-Forwarded-User", None))),
                a=str(self.action),
                s=str(source)))

            return True
        else:
            logger.info("permission denied - user: {u} action: {a} source: {s}".format(
                u=str(request.headers.get("X-Forwarded-Email",
                      request.headers.get("X-Forwarded-User", None))),
                a=str(self.action),
                s=str(source)))

            return False


class IsAuthenticatedXForwardedRBAC(IsAuthenticatedAction):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:

        request: typing.Union[Request, WebSocket] = info.context["request"]

        group_to_role = info.context["request"].app.config.get(
            "KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP", None)

        role_to_action = info.context["request"].app.config.get(
            "KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP", None)

        if not group_to_role:
            logger.warning(
                "KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP is not set in the config, all actions will be denied.")
            return False

        user_groups = request.headers.get("X-Forwarded-Groups", None)

        if not user_groups:
            logger.warning(
                "X-Forwarded-Groups header is not set, all actions will be denied.")
            return False

        for group in user_groups.split(","):
            if group_to_role.get(group, None):
                role = group_to_role[group]
                if role_to_action.get(role, None):
                    if self.action in role_to_action[role]:
                        logger.info("permission granted - user: {u} role: {r} action: {a} source: {s}".format(
                            u=str(request.headers.get("X-Forwarded-Email",
                                  request.headers.get("X-Forwarded-User", None))),
                            r=str(role),
                            a=str(self.action),
                            s=str(source)))
                        return True

        logger.info("permission denied - user: {u} action: {a} source: {s}".format(
            u=str(request.headers.get("X-Forwarded-Email",
                  request.headers.get("X-Forwarded-User", None))),
            a=str(self.action),
            s=str(source)))

        return False
