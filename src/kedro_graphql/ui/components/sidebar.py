import dash
import dash_bootstrap_components as dbc
from dash import html

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "backgroundColor": "#f8f9fa",
}



def sidebar(title = "Sidebar", description = "A simple sidebar layout with navigation links"):
    return html.Div(
        [
            html.H2(title, className="display-4"),
            html.Hr(),
            html.P(
                description, className="lead"
            ),
            dbc.Nav(
                [
                    dbc.NavLink(f"{page['name']}", href=page["relative_path"]) for page in dash.page_registry.values() if page["name"] not in ["Run", "Progress", "Submit"]
                ],
                vertical=True,
                pills=True,
            ),
        ],
        style=SIDEBAR_STYLE,
    )
