"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
import param
from kedro_graphql.client import KedroGraphqlClient

# pn.extension(theme="dark")


class NavigationSidebarButton(pn.viewable.Viewer):
    component = param.String(default="pipelines")
    name = param.String(default="pipelines")
    config = param.Dict(default={})

    def navigate(self, event):
        pn.state.location.pathname = self.config["KEDRO_GRAPHQL_UI_BASEPATH"]
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
    config = param.Dict(default={})
    id = param.String(default=None)
    pipeline = param.String(default=None)
    client = param.ClassSelector(class_=KedroGraphqlClient)
    component_map = param.Dict(default={})
    viz_static = param.String(default="")

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends("client", "id", "pipeline", "component", "viz_static")
    async def build_component(self):
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        params = {}
        required_params = self.config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"][self.component]["params"]
        for param in required_params:
            if param == "client":
                params[param] = self.client
            if param == "id":
                params[param] = self.id
            if param == "pipeline":
                params[param] = self.pipeline
            if param == "viz_static":
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

    def __init__(self, title="kedro-graphql", config=None, client=None, viz_static=None):
        super().__init__(
            title=config["KEDRO_GRAPHQL_UI_TITLE"],
            sidebar_width=200)
        for key, value in config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"].items():
            if value["sidebar"]:
                next_button = NavigationSidebarButton(name=key, config=config)
                pn.state.location.sync(next_button, {"component": "component"})
                self.sidebar.append(next_button)

        self.main.append(TemplateMainFactory(client=client, viz_static=viz_static, config=config,
                         component_map=config["KEDRO_GRAPHQL_UI_COMPONENT_MAP"]))

        pn.state.location.pathname = config["KEDRO_GRAPHQL_UI_BASEPATH"]
        pn.state.location.sync(
            self, {"component": "component", "id": "id", "pipeline": "pipeline"})
