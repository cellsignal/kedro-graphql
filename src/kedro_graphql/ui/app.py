"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
from kedro_graphql.ui.components.template import KedroGraphqlMaterialTemplate
# from kedro_graphql.client import KedroGraphqlClient
# from kedro_graphql.ui.decorators import discover_plugins
from importlib import import_module
import tempfile
import yaml

pn.extension(design='material', global_css=[
             ':root { --design-primary-color: black; }'])


def template_factory(spec={}):
    """Factory function to create a Kedro GraphQL UI template.

    Args:
        spec (dict): The specification for the UI, containing configuration and pages.
    Returns:
        dict: A dictionary mapping the base URL to a function that builds the template.
    """

    def build_template():
        return KedroGraphqlMaterialTemplate(spec=spec)

    return {spec["panel_get_server_kwargs"]["base_url"]: build_template}


def start_ui(config={}, spec=""):
    """Start the Kedro GraphQL UI application.

    Args:
        config (dict): Configuration dictionary.
        spec (str): Path to the YAML specification file for the UI.
    """

    # load the UI yaml specification
    with open(spec) as stream:
        try:
            spec = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # import components specified in UI spec for pages
    for key, value in spec["pages"].items():
        module_path, class_name = value["module"].rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        module_class = getattr(module, class_name)
        spec["pages"][key]["module"] = module_class
        print("imported module: " +
              str(module_class) + " for page: " + str(key))

    # import additinal modules to enable plugin discovery
    # e.g. @gql_form, @gql_data, etc...
    imports = [i.strip() for i in spec["config"]["imports"]]
    for i in imports:
        import_module(i)

    import sh

    with tempfile.TemporaryDirectory() as tmpdirname:
        sh.kedro("viz", "build")
        sh.mv("build", tmpdirname + "/build")

        pn.config.reuse_sessions = True
        pn.config.admin = True
        pn.config.global_loading_spinner = True
        # client = KedroGraphqlClient(
        # uri_graphql=spec["config"]["client_uri_graphql"], uri_ws=spec["config"]["client_uri_ws"])

        if spec["panel_get_server_kwargs"].get("static_dirs", None):
            spec["panel_get_server_kwargs"]["static_dirs"]["/pipeline/viz-build"] = str(
                tmpdirname + "/build")
        else:
            spec["panel_get_server_kwargs"]["static_dirs"] = {
                "/pipeline/viz-build": str(tmpdirname + "/build")}

        # spec["config"]["client"] = client
        pn.serve(template_factory(spec=spec), **spec["panel_get_server_kwargs"])
