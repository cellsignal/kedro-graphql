"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
import param
from kedro_graphql.config import config

pn.extension(theme="dark")

class KedroGraphqlMaterialTemplate(pn.template.MaterialTemplate):

    def __init__(self, title = "kedro-graphql"):
        if pn.state.location.pathname == config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + "/cards":
            b0_type = "default"
            b0_icon = "chevron-right-pipe"
        else:
            b0_type = "primary"
            b0_icon = None

        pipelines_button = pn.widgets.Button(name='Pipelines', button_type=b0_type, sizing_mode="stretch_width", icon = b0_icon)

        if pn.state.location.pathname == config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + "/search":
            b1_type = "default"
            b1_icon = "chevron-right-pipe"
        else:
            b1_type = "primary"
            b1_icon = None


        search_button = pn.widgets.Button(name='Search', button_type=b1_type, sizing_mode="stretch_width", icon = b1_icon)
        
        pn.bind(self.navigate, pipelines_button, name = "pipelines", watch=True),
        pn.bind(self.navigate, search_button, name = "search", watch=True),
        sidebar = [
          pipelines_button,
          search_button,
        ]
        super().__init__(title = config["KEDRO_GRAPHQL_VIZ_TITLE"], sidebar = sidebar)

    def navigate(self, event, name = None):
        if name == "pipelines":
            pn.state.location.pathname = config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + "/cards"
            pn.state.location.search = ''
            pn.state.location.reload = True
        if name == "search":
            pn.state.location.pathname = config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + "/search"
            pn.state.location.search = ''
            pn.state.location.reload = True
