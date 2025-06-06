"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
import param
from kedro_graphql.client import KedroGraphqlClient

# pn.extension(theme="dark")


class NavigationSidebarButton(pn.viewable.Viewer):
    """A button for navigating the sidebar in the Kedro GraphQL UI.
    This button is used to navigate to different pages in the UI, such as pipelines, nodes, or data catalog.
    It updates the URL to reflect the current page and changes its appearance based on whether it is the active page.

    Attributes:
        page (str): The name of the page this button navigates to.
        name (str): The display name of the button.
        spec (dict): The specification for the UI, including configuration and pages.
    """
    page = param.String(default="pipelines")
    name = param.String(default="pipelines")
    spec = param.Dict(default={})

    def navigate(self, event):
        """Navigate to the specified page."""
        pn.state.location.pathname = self.spec["config"]["base_url"]
        pn.state.location.search = "?page="+self.name.lower()

    async def build_button(self):
        """Builds the navigation button for the sidebar.
        This button will change its appearance based on whether it is the current page.

        Returns:
            pn.widgets.Button: A button that navigates to the specified page.
        """
        if self.page == self.name.lower():
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
    """A factory for building the main content of the Kedro GraphQL UI template.
    This component dynamically builds the main content based on the current page specified in the URL.
    It uses the `spec` dictionary to determine which module to load for each page.

    Attributes:
        page (str): The current page to display in the main content.
        spec (dict): The specification for the UI, including configuration and pages.
    """
    page = param.String(default="pipelines")
    spec = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends("page", "spec")
    async def build_page(self):
        """Builds the main content of the template based on the current page."""
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        if self.spec["pages"][self.page].get("params", False):
            params = self.spec["pages"][self.page]["params"]
        else:
            params = {}
        yield self.spec["pages"][self.page]["module"](spec=self.spec, **params)

    def __panel__(self):
        pn.state.location.sync(
            self, {"page": "page"})

        return self.build_page


class KedroGraphqlMaterialTemplate(pn.template.MaterialTemplate):
    """A Material Design template for the Kedro GraphQL UI.
    This template includes a sidebar for navigation and a main content area that 
    displays different pages based on the current URL.
    It uses the `spec` dictionary to configure the sidebar and main content.

    Attributes:
        title (str): The title of the template.
        sidebar_width (int): The width of the sidebar in pixels.
        page (str): The current page to display in the main content.
        spec (dict): The specification for the UI, including configuration and pages.
    """

    page = param.String(default="pipelines")
    spec = param.Dict(default={})

    def __init__(self, title="kedro-graphql", spec=None):
        super().__init__(
            title=spec["config"]["site_name"],
            sidebar_width=200)
        for nav in spec["nav"]["sidebar"]:
            next_button = NavigationSidebarButton(name=nav["name"], spec=spec)
            pn.state.location.sync(next_button, {"page": "page"})
            self.sidebar.append(next_button)

        self.main.append(TemplateMainFactory(spec=spec))

        pn.state.location.pathname = spec["config"]["base_url"]
        pn.state.location.sync(
            self, {"page": "page"})
