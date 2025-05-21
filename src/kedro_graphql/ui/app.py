"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
from kedro_graphql.ui.components.template import KedroGraphqlMaterialTemplate
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.ui.decorators import discover_plugins
import tempfile

pn.extension(design='material', global_css=[
             ':root { --design-primary-color: black; }'])


def template_factory(config={}, client=None, viz_static=None):

    def build_template():
        return KedroGraphqlMaterialTemplate(client=client, config=config, viz_static=viz_static)

    return {config["KEDRO_GRAPHQL_UI_BASEPATH"]: build_template}


def start_ui(config={}):

    # import components specified in component map
    for key, value in config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"].items():
        module_path, class_name = value["component"].rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        component_class = getattr(module, class_name)
        config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"][key]["component"] = component_class

    import sh

    with tempfile.TemporaryDirectory() as tmpdirname:
        sh.kedro("viz", "build")
        sh.mv("build", tmpdirname + "/build")

        pn.config.reuse_sessions = True
        pn.config.admin = True
        pn.config.global_loading_spinner = True
        discover_plugins(config)

        client = KedroGraphqlClient(
            uri_graphql=config["KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL"], uri_ws=config["KEDRO_GRAPHQL_CLIENT_URI_WS"])
        pn.serve(template_factory(config=config, client=client, viz_static=tmpdirname +
                 "/build/"), admin=True, port=5006, static_dirs={"/pipeline/viz-build": str(tmpdirname + "/build")})
