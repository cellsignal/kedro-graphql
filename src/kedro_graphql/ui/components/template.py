"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
import param
from kedro_graphql.config import config
from kedro_graphql.client import KedroGraphqlClient

# pn.extension(theme="dark")


class NavigationSidebarButton(pn.viewable.Viewer):
    component = param.String(default="pipelines")
    name = param.String(default="pipelines")

    def navigate(self, event):
        pn.state.location.pathname = config["KEDRO_GRAPHQL_UI_BASEPATH"]
        pn.state.location.search = "?component="+self.name.lower()

    async def build_button(self):
        if self.component == self.name.lower():
            b0_type = "primary"
            b0_icon = "chevron-right-pipe"
        else:
            b0_type = "default"
            b0_icon = None

        button = pn.widgets.Button(
            name=self.name, button_type=b0_type, sizing_mode="stretch_width", icon=b0_icon)
        pn.bind(self.navigate, button, watch=True)
        return button

    def __panel__(self):
        return self.build_button


class TemplateMainFactory(pn.viewable.Viewer):
    component = param.String(default="pipelines")
    id = param.String(default=None)
    pipeline = param.String(default=None)
    client = param.ClassSelector(class_=KedroGraphqlClient)
    component_map = param.Dict(default={})
    viz_static = param.String(default="")

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends("client", "pipeline", "component")
    async def build_component(self):
        print(self.viz_static)
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        params = {}
        required_params = config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"][self.component]["params"]
        for param in required_params:
            if param == "client":
                params[param] = self.client
            elif param == "pipeline":
                params[param] = self.pipeline
            elif param == "viz_static":
                params[param] = self.viz_static
        yield self.component_map[self.component]["component"](**params)

    def __panel__(self):
        pn.state.location.sync(
            self, {"component": "component", "id": "id", "pipeline": "pipeline"})
        return self.build_component


class KedroGraphqlMaterialTemplate(pn.template.MaterialTemplate):

    component = param.String(default="pipelines")
    id = param.String(default="")
    pipeline = param.String(default="")

    def __init__(self, title="kedro-graphql", client=None, viz_static=None):
        super().__init__(
            title=config["KEDRO_GRAPHQL_UI_TITLE"],
            sidebar_width=200)

        for key, value in config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"].items():
            if value["sidebar"]:
                next_button = NavigationSidebarButton(name=key)
                pn.state.location.sync(next_button, {"component": "component"})
                self.sidebar.append(next_button)

        self.main.append(TemplateMainFactory(client=client, viz_static=viz_static,
                         component_map=config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"]))

        pn.state.location.pathname = config["KEDRO_GRAPHQL_UI_BASEPATH"]
        pn.state.location.sync(
            self, {"component": "component", "id": "id", "pipeline": "pipeline"})
