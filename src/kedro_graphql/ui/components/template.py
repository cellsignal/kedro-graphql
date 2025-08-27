"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
from panel.custom import JSComponent
import param
from kedro_graphql.client import KedroGraphqlClient


# pn.extension(theme="dark")
pn.extension("modal")
pn.extension(
    disconnect_notification='Connection lost, try reloading the page!',
    ready_notification='Application fully loaded.',
    template='bootstrap'
)


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
        pn.state.location.pathname = self.spec["panel_get_server_kwargs"]["prefix"]
        pn.state.location.search = "?page=" + self.name.lower()

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
            name=self.name,
            button_type=b0_type,
            sizing_mode="stretch_width",
            icon=b0_icon
        )
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

        return pn.Column(self.build_page)


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

    def user_menu_action(self, event, user_info_modal, login_link, logout_link):
        """ Handles user menu actions such as showing user information, logging in, or logging out.
        Args:
            event (str): The action triggered by the user menu.
            user_info_modal (pn.Modal): The modal to display user information.
            login_link (str): The URL for the login endpoint.
            logout_link (str): The URL for the logout endpoint.
        """
        if event == "User Information":
            user_info_modal.show()
        elif event == "Login":
            pn.state.location.pathname = login_link
            pn.state.location.search = ""
            pn.state.location.reload = True
        elif event == "Logout":
            pn.state.location.pathname = logout_link
            pn.state.location.search = ""
            pn.state.location.reload = True

    async def build_user_menu(self):
        """Asynchronously retrieves the user context for the template.
        This method can be overridden to provide custom user context data.
        """
        # if hasattr(pn.state, "user_info") and pn.state.user_info:
        # user = pn.state.user_info.get("name", False) or pn.state.user or "Guest"

        user = pn.state.headers.get("X-Forwarded-User", None) or pn.state.headers.get("X-Auth-Request-User", None)

        if user:
            email = pn.state.headers.get("X-Forwarded-Email", None) or pn.state.headers.get("X-Auth-Request-Email", None)
            groups = pn.state.headers.get("X-Forwarded-Groups", None) or pn.state.headers.get("X-Auth-Request-Groups", None)
            user_info = {"user": user, "email": email, "groups": groups}
        else:
            user = "Guest"
            user_info = {"user": "Guest", "email": "Guest", "groups": None}

        user_menu_items = [("User Information", "User Information")]

        login_link = self.spec["panel_get_server_kwargs"].get(
            "login_endpoint", "/login")
        logout_link = self.spec["panel_get_server_kwargs"].get(
            "logout_endpoint", "/logout")

        if user == "Guest":
            if pn.config.oauth_provider:
                user_menu_items.append("Login")
            elif pn.config.basic_auth:
                user_menu_items.append("Login")
        else:
            user_menu_items.append("Logout")

        user_menu = pn.widgets.MenuButton(name=user_info["email"].split("@")[0], icon="circle-letter-" + user_info["email"][0].lower(
        ), icon_size="2em", items=user_menu_items, sizing_mode="stretch_width",)
        user_info_modal = pn.Modal(user_info, name='User Information',
                                   margin=20, background_close=True, show_close_button=True)
        pn.bind(self.user_menu_action, user_menu.param.clicked,
                user_info_modal, login_link, logout_link, watch=True)
        yield pn.Column(pn.Row(user_menu), pn.Row(user_info_modal, height=0)
                        )

    def init_client(self, spec):
        """Initializes the Kedro GraphQL client with the provided specification.
        This method sets up the client to connect to the GraphQL API and WebSocket.

        Args:
            spec (dict): The specification for the UI, including configuration and pages.
        """

        if pn.state.cookies:
            cookies = pn.state.cookies
        else:
            cookies = None

        client = KedroGraphqlClient(
            uri_graphql=spec["config"]["client_uri_graphql"],
            uri_ws=spec["config"]["client_uri_ws"],
            cookies=cookies
        )

        spec["config"]["client"] = client
        return spec

    def __init__(self, title="kedro-graphql", spec=None):
        """Initializes the KedroGraphqlMaterialTemplate with a title and specification.
        Args:
            title (str): The title of the template.
            spec (dict): The specification for the UI, including configuration and pages.
        """
        super().__init__(
            title=spec["panel_get_server_kwargs"]["title"],
            sidebar_width=200)

        self.spec = self.init_client(spec)
        self.sidebar.append(self.build_user_menu)
        self.sidebar.append(pn.layout.Divider())
        for nav in spec["nav"]["sidebar"]:
            next_button = NavigationSidebarButton(name=nav["name"], spec=spec)
            pn.state.location.sync(next_button, {"page": "page"})
            self.sidebar.append(next_button)

        self.main.append(pn.Column(TemplateMainFactory(spec=spec)))
        # pn.state.location.pathname = spec["panel_get_server_kwargs"]["prefix"]
        pn.state.location.sync(
            self, {"page": "page"})


class NavigationSidebarButtonV2(pn.viewable.Viewer):
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
        pn.state.location.pathname = self.spec["panel_get_server_kwargs"]["prefix"] + self.name.lower()
        pn.state.location.search = ""
        pn.state.location.reload = True

    async def build_button(self):
        """Builds the navigation button for the sidebar.
        This button will change its appearance based on whether it is the current page.

        Returns:
            pn.widgets.Button: A button that navigates to the specified page.
        """
        if pn.state.location.pathname == "/" + self.name.lower():
            b0_type = "primary"
            b0_icon = "chevron-right-pipe"
        else:
            b0_type = "default"
            b0_icon = None

        button = pn.widgets.Button(
            name=self.name,
            button_type=b0_type,
            sizing_mode="stretch_width",
            icon=b0_icon
        )
        pn.bind(self.navigate, button, watch=True)
        yield button

    def __panel__(self):
        return self.build_button


class KedroGraphqlMaterialTemplateV2(pn.template.MaterialTemplate):
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
    spec = param.Dict(default={})

    def user_menu_action(self, event, user_info_modal, login_link, logout_link):
        """ Handles user menu actions such as showing user information, logging in, or logging out.
        Args:
            event (str): The action triggered by the user menu.
            user_info_modal (pn.Modal): The modal to display user information.
            login_link (str): The URL for the login endpoint.
            logout_link (str): The URL for the logout endpoint.
        """
        if event == "User Information":
            user_info_modal.show()
        elif event == "Login":
            pn.state.location.pathname = login_link
            pn.state.location.search = ""
            pn.state.location.reload = True
        elif event == "Logout":
            pn.state.location.pathname = logout_link
            pn.state.location.search = ""
            pn.state.location.reload = True

    async def build_user_menu(self):
        """Asynchronously retrieves the user context for the template.
        This method can be overridden to provide custom user context data.
        """
        
        user = pn.state.headers.get("X-Forwarded-User", None) or pn.state.headers.get("X-Auth-Request-User", None)

        if user:
            email = pn.state.headers.get("X-Forwarded-Email", None) or pn.state.headers.get("X-Auth-Request-Email", None)
            groups = pn.state.headers.get("X-Forwarded-Groups", None) or pn.state.headers.get("X-Auth-Request-Groups", None)
            user_info = {"user": user, "email": email, "groups": groups}
        else:
            user = "Guest"
            user_info = {"user": "Guest", "email": "Guest", "groups": None}

        user_menu_items = [("User Information", "User Information")]

        login_link = self.spec["panel_get_server_kwargs"].get(
            "login_endpoint", "/login")
        logout_link = self.spec["panel_get_server_kwargs"].get(
            "logout_endpoint", "/logout")

        if user == "Guest":
            if pn.config.oauth_provider:
                user_menu_items.append("Login")
            elif pn.config.basic_auth:
                user_menu_items.append("Login")
        else:
            user_menu_items.append("Logout")

        user_menu = pn.widgets.MenuButton(name=user_info["email"].split("@")[0], icon="circle-letter-" + user_info["email"][0].lower(
        ), icon_size="2em", items=user_menu_items, sizing_mode="stretch_width",)
        user_info_modal = pn.Modal(user_info, name='User Information',
                                   margin=20, background_close=True, show_close_button=True)
        pn.bind(self.user_menu_action, user_menu.param.clicked,
                user_info_modal, login_link, logout_link, watch=True)
        yield pn.Column(pn.Row(user_menu), pn.Row(user_info_modal, height=0)
                        )

    def init_client(self, spec):
        """Initializes the Kedro GraphQL client with the provided specification.
        This method sets up the client to connect to the GraphQL API and WebSocket.

        Args:
            spec (dict): The specification for the UI, including configuration and pages.
        """

        if pn.state.cookies:
            cookies = pn.state.cookies
        else:
            cookies = None

        client = KedroGraphqlClient(
            uri_graphql=spec["config"]["client_uri_graphql"],
            uri_ws=spec["config"]["client_uri_ws"],
            cookies=cookies
        )

        spec["config"]["client"] = client
        return spec

    def __init__(self, title="kedro-graphql", spec=None, main=[]):
        """Initializes the KedroGraphqlMaterialTemplate with a title and specification.
        Args:
            title (str): The title of the template.
            spec (dict): The specification for the UI, including configuration and pages.
        """
        super().__init__(
            title=spec["panel_get_server_kwargs"]["title"],
            base_url=spec["panel_get_server_kwargs"]["prefix"],
            sidebar_width=200)

        self.spec = self.init_client(spec)
        self.sidebar.append(self.build_user_menu)
        self.sidebar.append(pn.layout.Divider())
        for nav in spec["nav"]["sidebar"]:
            next_button = NavigationSidebarButtonV2(name=nav["name"], spec=spec)
            self.sidebar.append(next_button)

        # fix for browser navigation with forward and back buttons
        fix = pn.pane.HTML("""
        <script>
        window.addEventListener('popstate', function(event) {
          window.location.replace(window.location.href);
        });
        </script>
        """)

        self.main.append(fix)
        self.main.append(main)
