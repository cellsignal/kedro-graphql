from importlib import import_module

from .logs.logger import logger

RESOLVER_PLUGINS = {}

TYPE_PLUGINS = {"query": [],
                "mutation": [],
                "subscription": []}


def discover_plugins(config):
    # discover plugins e.g. decorated functions e.g @gql_query, etc...
    for i in config["KEDRO_GRAPHQL_IMPORTS"]:
        import_module(i)


class NameConflictError(BaseException):
    """Raise for errors in adding plugins do to the same name."""


def gql_resolver(name):

    if name in RESOLVER_PLUGINS:
        raise NameConflictError(
            f"Plugin name conflict: '{name}'. Double check"
            " that all plugins have unique names."
        )

    def register_plugin(plugin_class):
        plugin = plugin_class()
        RESOLVER_PLUGINS[name] = plugin
        logger.info("registered resolver plugin '" + name + "' " + str(RESOLVER_PLUGINS[name]))
        return plugin

    return register_plugin


def gql_query():

    def register_plugin(plugin_class):
        TYPE_PLUGINS["query"].append(plugin_class)
        logger.info("registered type plugin 'query': " + str(plugin_class))
        return plugin_class

    return register_plugin


def gql_mutation():

    def register_plugin(plugin_class):
        TYPE_PLUGINS["mutation"].append(plugin_class)
        logger.info("registered type plugin 'query': " + str(plugin_class))
        return plugin_class

    return register_plugin


def gql_subscription():

    def register_plugin(plugin_class):
        TYPE_PLUGINS["subscription"].append(plugin_class)
        logger.info("registered type plugin 'query': " + str(plugin_class))
        return plugin_class

    return register_plugin
