import os
from importlib import import_module
from .logs.logger import logger

RESOLVER_PLUGINS = {}
#from .config import RESOLVER_PLUGINS
TYPE_PLUGINS = {"query":[],
                "mutation":[],
                "subscription":[]}
#from .config import TYPE_PLUGINS
def discover_plugins(config):
    ## discover plugins e.g. decorated functions e.g @gql_query, etc...
    imports = [i.strip() for i in config["KEDRO_GRAPHQL_IMPORTS"].split(",") if len(i.strip()) > 0]
    for i in imports:
        import_module(i)



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
        logger.info("registered resolver plugin '" + name + "' " + str(RESOLVER_PLUGINS[name]))
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
        logger.info("registered type plugin 'query': " + str(plugin_class))
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
        logger.info("registered type plugin 'query': " + str(plugin_class))
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
        logger.info("registered type plugin 'query': " + str(plugin_class))
        return plugin_class

    return register_plugin