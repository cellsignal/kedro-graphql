import os
from .config import RESOLVER_PLUGINS
from .config import TYPE_PLUGINS

class NameConflictError(BaseException):
    """Raise for errors in adding plugins do to the same name."""

def gql_resolver(name):
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

def gql_query():
    """
    """
    ## raise warning if same class is registered twice?
    ##if type not in TYPE_PLUGINS.keys():
    ##    raise KeyError(
    ##        f"Type plugin error: '{type}', must be one of ['query', 'mutation', or 'subscription']"
    ##    )

    def register_plugin(plugin_class):
        TYPE_PLUGINS["query"].append(plugin_class)
        print("registered type plugin 'query':", plugin_class)
        return plugin_class

    return register_plugin

def gql_mutation():
    """
    """
    ## raise warning if same class is registered twice?
    ##if type not in TYPE_PLUGINS.keys():
    ##    raise KeyError(
    ##        f"Type plugin error: '{type}', must be one of ['query', 'mutation', or 'subscription']"
    ##    )

    def register_plugin(plugin_class):
        TYPE_PLUGINS["mutation"].append(plugin_class)
        print("registered type plugin 'query':", plugin_class)
        return plugin_class

    return register_plugin

def gql_subscription():
    """
    """
    ## raise warning if same class is registered twice?
    ##if type not in TYPE_PLUGINS.keys():
    ##    raise KeyError(
    ##        f"Type plugin error: '{type}', must be one of ['query', 'mutation', or 'subscription']"
    ##    )

    def register_plugin(plugin_class):
        TYPE_PLUGINS["subscription"].append(plugin_class)
        print("registered type plugin 'query':", plugin_class)
        return plugin_class

    return register_plugin