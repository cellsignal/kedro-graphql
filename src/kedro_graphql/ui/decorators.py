from importlib import import_module
from kedro_graphql.logs.logger import logger

UI_PLUGINS = {"FORMS": {},
              "DATA": {},
              "DASHBOARD": {},
              }


def discover_plugins(config):
    # call this when starting app to discover plugins
    # discover plugins e.g. decorated functions e.g @gql_form, etc...
    imports = [i.strip()
               for i in config["KEDRO_GRAPHQL_IMPORTS"].split(",") if len(i.strip()) > 0]
    for i in imports:
        import_module(i)


def ui_form(pipeline):
    """
    Args:
        pipeline (str): name of pipeline.
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
    """
    Args:
        pipeline (str): name of pipeline
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
    """
    Args:
        pipeline (str): name of pipeline
    """
    def register_plugin(plugin_class):
        if UI_PLUGINS["DASHBOARD"].get(pipeline, False):
            UI_PLUGINS["DASHBOARD"][pipeline].append(plugin_class)
        else:
            UI_PLUGINS["DASHBOARD"][pipeline] = [plugin_class]
        logger.info("registered ui_dashboard plugin: " + str(plugin_class))
        return plugin_class

    return register_plugin
