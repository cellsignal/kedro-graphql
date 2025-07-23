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
    """Base class for authentication permissions using actions.
    """
    message = "User is not authenticated"
    error_extensions = {"code": "UNAUTHORIZED"}

    def __init__(self, action):
        """Initialize the permission with a specific action.
        """
        self._all_actions = ["create_pipeline",
                             "read_pipeline",
                             "read_pipelines",
                             "update_pipeline",
                             "delete_pipeline",
                             "read_pipeline_template",
                             "read_pipeline_templates",
                             "create_dataset",
                             "read_dataset",
                             "subscribe_to_events",
                             "subscribe_to_logs",
                             "create_event"]
        self.action = action

    @staticmethod
    def get_user_info(info: strawberry.Info) -> typing.Optional[typing.Any]:
        """Get user information from the request context.
        This method should be overridden in subclasses if needed.

        Args:
            info: Strawberry Info object containing the request context.

        Returns:
            Optional[Any]: User information, or None if not available.
        """
        raise NotImplementedError(
            "get_user_info method must be implemented in subclasses")

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        """Check if the user has permission for the specified action.
        This method should be overridden in subclasses.

        Kwargs:
            source: The source of the request, typically the fields of the GraphQL query.
            info: Strawberry Info object containing the request context.
            **kwargs: Additional keyword arguments that may be used in the future.

        Returns:
            bool: True if the user has permission, False otherwise.
        """
        raise NotImplementedError


class IsAuthenticatedAlways(IsAuthenticatedAction):
    """Permission class that always grants access."""

    @staticmethod
    def get_user_info(info: strawberry.Info) -> typing.Optional[typing.Any]:
        """Get user information from the request context.
        This method returns None since this permission always grants access.

        Args:
            info: Strawberry Info object containing the request context.

        Returns:
            Optional[Any]: Always returns None.
        """
        return {"user": None, "email": None, "groups": None}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        """Always grants permission regardless of user authentication.

        Kwargs:
            source: The source of the request, typically the fields of the GraphQL query.
            info: Strawberry Info object containing the request context.
            **kwargs: Additional keyword arguments that may be used in the future.

        Returns:
            bool: Always returns True, granting permission.
        """

        logger.info(
            "authentication disabled - permission granted - user=None, action={a}, source={s}".format(s=str(source), a=str(self.action)))
        return True


class IsAuthenticatedXForwardedEmail(IsAuthenticatedAction):
    """Permission class that checks for X-Forwarded-Email header."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_user_info(info: strawberry.Info) -> typing.Optional[typing.Any]:
        request: typing.Union[Request, WebSocket] = info.context["request"]
        return {"email": request.headers.get("X-Forwarded-Email", None),
                "user": request.headers.get("X-Forwarded-User", None)}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        """Check if the user has permission based on X-Forwarded-Email header.
        If the header is present, permission is granted.
        If the header is not present, permission is denied.

        Kwargs:
            source: The source of the request, typically the fields of the GraphQL query.
            info: Strawberry Info object containing the request context.
            **kwargs: Additional keyword arguments that may be used in the future.

        Returns:
            bool: True if the user has permission, False otherwise.
        """
        request: typing.Union[Request, WebSocket] = info.context["request"]
        if request.headers.get("X-Forwarded-Email", None):
            logger.info("permission granted - user={u}, action={a}, source={s}".format(
                u=str(request.headers.get("X-Forwarded-Email",
                      request.headers.get("X-Forwarded-User", None))),
                a=str(self.action),
                s=str(source)))

            return True
        else:
            logger.info("permission denied - user={u}, action={a}, source={s}".format(
                u=str(request.headers.get("X-Forwarded-Email",
                      request.headers.get("X-Forwarded-User", None))),
                a=str(self.action),
                s=str(source)))

            return False


class IsAuthenticatedXForwardedRBAC(IsAuthenticatedAction):
    """Permission class that checks for X-Forwarded-Groups header and RBAC mapping."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_user_info(info: strawberry.Info) -> typing.Optional[typing.Any]:
        request: typing.Union[Request, WebSocket] = info.context["request"]
        return {"email": request.headers.get("X-Forwarded-Email", None),
                "groups": request.headers.get("X-Forwarded-Groups", None),
                "user": request.headers.get("X-Forwarded-User", None)}

    def has_permission(
        self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        """Check if the user has permission based on X-Forwarded-Groups header and RBAC mapping.
        If the header is present and the user belongs to a group that has the required role for
        the specified action, permission is granted.
        If the header is not present or the user does not belong to a group with the required
        role for the specified action, permission is denied.

        Kwargs:
            source: The source of the request, typically the fields of the GraphQL query.
            info: Strawberry Info object containing the request context.
            **kwargs: Additional keyword arguments that may be used in the future.

        Returns:
            bool: True if the user has permission, False otherwise.
        """
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
                        logger.info("permission granted - user={u}, role={r}, action={a}, source={s}".format(
                            u=str(request.headers.get("X-Forwarded-Email",
                                  request.headers.get("X-Forwarded-User", None))),
                            r=str(role),
                            a=str(self.action),
                            s=str(source)))
                        return True

        logger.info("permission denied - user:={u}, action={a}, source={s}".format(
            u=str(request.headers.get("X-Forwarded-Email",
                  request.headers.get("X-Forwarded-User", None))),
            a=str(self.action),
            s=str(source)))

        return False
