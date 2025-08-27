from importlib import import_module
from kedro_graphql.logs.logger import logger

UI_PLUGINS = {"FORMS": {},
              "DATA": {},
              "DASHBOARD": {},
              }


def discover_plugins(config):
    """Discover and import plugins based on the configuration.
    Args:
        config (dict): Configuration dictionary containing the imports.
    """
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


def ui_form(pipeline):
    """Register a UI form plugin for a specific pipeline.

    Args:
        pipeline (str): Name of the pipeline for which the form is registered.
    """

    def register_plugin(plugin_class):
        if UI_PLUGINS["FORMS"].get(pipeline, False):
            UI_PLUGINS["FORMS"][pipeline].append(plugin_class)
        else:
            UI_PLUGINS["FORMS"][pipeline] = [plugin_class]
        logger.info("registered ui_form plugin: " + str(plugin_class))
        return plugin_class

    return register_plugin


def ui_data(pipeline):
    """Register a UI data plugin for a specific pipeline.

    Args:
        pipeline (str): Name of the pipeline for which the data plugin is registered.
    """
    def register_plugin(plugin_class):
        if UI_PLUGINS["DATA"].get(pipeline, False):
            UI_PLUGINS["DATA"][pipeline].append(plugin_class)
        else:
            UI_PLUGINS["DATA"][pipeline] = [plugin_class]
        logger.info("registered ui_data plugin: " + str(plugin_class))
        return plugin_class

    return register_plugin


def ui_dashboard(pipeline):
    """Register a UI dashboard plugin for a specific pipeline.

    Args:
        pipeline (str): Name of the pipeline for which the dashboard plugin is registered.
    """
    def register_plugin(plugin_class):
        if UI_PLUGINS["DASHBOARD"].get(pipeline, False):
            UI_PLUGINS["DASHBOARD"][pipeline].append(plugin_class)
        else:
            UI_PLUGINS["DASHBOARD"][pipeline] = [plugin_class]
        logger.info("registered ui_dashboard plugin: " + str(plugin_class))
        return plugin_class

    return register_plugin
