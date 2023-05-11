import os
from .config import RESOLVER_PLUGINS
from .config import TYPE_PLUGINS

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

def gql_type(type):
    """
    """

    if type not in TYPE_PLUGINS.keys():
        raise KeyError(
            f"Type plugin error: '{type}', must be one of ['query', 'mutation', or 'subscription']"
        )

    def register_plugin(plugin_class):
        plugin = plugin_class()
        TYPE_PLUGINS[type] = plugin
        print("registered type plugin","'" + type + "'", TYPE_PLUGINS[type])
        return plugin

    return register_plugin