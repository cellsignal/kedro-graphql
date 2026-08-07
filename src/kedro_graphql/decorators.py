from importlib import import_module

from .config import KedroGraphQLConfig
from .logs.logger import logger

TYPE_PLUGINS = {"query": [],
                "mutation": [],
                "subscription": []}


def discover_plugins(config: KedroGraphQLConfig):
    # discover plugins e.g. decorated functions e.g @gql_query, etc...
    for i in config.imports:
        import_module(i)


def gql_query():

    def register_plugin(plugin_class):
        TYPE_PLUGINS["query"].append(plugin_class)
        logger.info("registered type plugin 'query': " + str(plugin_class))
        return plugin_class

    return register_plugin


def gql_mutation():

    def register_plugin(plugin_class):
        TYPE_PLUGINS["mutation"].append(plugin_class)
        logger.info("registered type plugin 'mutation': " + str(plugin_class))
        return plugin_class

    return register_plugin


def gql_subscription():

    def register_plugin(plugin_class):
        TYPE_PLUGINS["subscription"].append(plugin_class)
        logger.info("registered type plugin 'subscription': " + str(plugin_class))
        return plugin_class

    return register_plugin
