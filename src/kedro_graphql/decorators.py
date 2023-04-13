import os
import importlib
RESOLVERS = {}

class NameConflictError(BaseException):
    """Raise for errors in adding plugins do to the same name."""

def gql(name):
    """
    """

    if name in RESOLVERS:
        raise NameConflictError(
            f"Plugin name conflict: '{name}'. Double check" \
            " that all plugins have unique names."
        )
    def register_plugin(plugin_class):
        plugin = plugin_class()
        RESOLVERS[name] = plugin
        return plugin

    return register_plugin
