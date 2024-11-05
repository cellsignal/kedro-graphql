from importlib import import_module
from kedro_graphql.logs.logger import logger

VIZ_PLUGINS = {"FORMS":{},
               "DATA":{}
              }

def discover_plugins(config):
    ## call this when starting app to discover plugins
    ## discover plugins e.g. decorated functions e.g @gql_form, etc...
    imports = [i.strip() for i in config["KEDRO_GRAPHQL_IMPORTS"].split(",") if len(i.strip()) > 0]
    for i in imports:
        import_module(i)

def viz_form(pipeline):
    """
    Args:
        pipeline (str): name of pipeline.
    """
    def register_plugin(plugin_class):
        if VIZ_PLUGINS["FORMS"].get(pipeline, False):
            VIZ_PLUGINS["FORMS"][pipeline].append(plugin_class)
        else:
            VIZ_PLUGINS["FORMS"][pipeline] = [plugin_class]
        logger.info("registered 'viz_form' plugin: " + str(plugin_class))
        return plugin_class

    return register_plugin

def viz_data(pipeline):
    """
    Args:
        pipeline (str): name of pipeline
    """
    def register_plugin(plugin_class):
        if VIZ_PLUGINS["DATA"].get(pipeline, False):
            VIZ_PLUGINS["DATA"][pipeline].append(plugin_class)
        else:
            VIZ_PLUGINS["DATA"][pipeline] = [plugin_class]
        logger.info("registered 'viz_data' plugin: " + str(plugin_class))
        return plugin_class

    return register_plugin