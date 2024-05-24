import dash
from dash import Dash, html, dcc, clientside_callback, Input, Output
import dash_bootstrap_components as dbc
from components.sidebar import sidebar

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.SANDSTONE],
    use_pages=True
)


# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "marginLeft": "18rem",
    "marginRight": "2rem",
    "padding": "2rem 1rem",
}


app.layout =  dbc.Container(
    [
        sidebar(title = "Kedro GraphQL", description = "A simple sidebar layout with navigation links"),
        html.Div(id="page-content", style=CONTENT_STYLE, children=[
            dash.page_container
        ]),
    ],
    fluid=True
)


if __name__ == '__main__':
    app.run(debug=True)