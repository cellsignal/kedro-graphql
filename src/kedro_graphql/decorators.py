from importlib import import_module

from .logs.logger import logger

RESOLVER_PLUGINS = {}

TYPE_PLUGINS = {"query": [],
                "mutation": [],
                "subscription": []}


def discover_plugins(config):
    # discover plugins e.g. decorated functions e.g @gql_query, etc...
    kedro_imports = config["KEDRO_GRAPHQL_IMPORTS"]
    
    # Handle both string and list types
    if isinstance(kedro_imports, str):
        imports = [i.strip() for i in kedro_imports.split(",") if len(i.strip()) > 0]
    elif isinstance(kedro_imports, list):
        imports = [i.strip() for i in kedro_imports if len(i.strip()) > 0]
    else:
        imports = []
    
    for i in imports:
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
