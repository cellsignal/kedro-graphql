"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
import param
from kedro_graphql.config import config
from kedro_graphql.ui.components.template_main_factory import TemplateMainFactory

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


class KedroGraphqlMaterialTemplate(pn.template.MaterialTemplate):

    component = param.String(default="pipelines")
    id = param.String(default="")
    pipeline = param.String(default="")

    def __init__(self, title="kedro-graphql", client=None, viz_static=None):
        super().__init__(
            title=config["KEDRO_GRAPHQL_UI_TITLE"])

        nav = ["Pipelines", "Search"]
        for n in nav:
            next_button = NavigationSidebarButton(name=n)
            pn.state.location.sync(next_button, {"component": "component"})
            # pn.bind(self.navigate, next_button, name=n, watch=True)
            self.sidebar.append(next_button)

        self.main.append(TemplateMainFactory(client=client, viz_static=viz_static))
        pn.state.location.pathname = config["KEDRO_GRAPHQL_UI_BASEPATH"]
        pn.state.location.sync(
            self, {"component": "component", "id": "id", "pipeline": "pipeline"})
