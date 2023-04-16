import os
from .config import RESOLVER_PLUGINS

class NameConflictError(BaseException):
    """Raise for errors in adding plugins do to the same name."""

def gql(name):
    """
    """

    if name in RESOLVER_PLUGINS:
        raise NameConflictError(
            f"Plugin name conflict: '{name}'. Double check" \
            " that all plugins have unique names."
        )
    def register_plugin(plugin_class):
        plugin = plugin_class()
        RESOLVER_PLUGINS[name] = plugin
        print("registered resolver plugin","'" + name + "'", RESOLVER_PLUGINS[name])
        return plugin

    return register_plugin
