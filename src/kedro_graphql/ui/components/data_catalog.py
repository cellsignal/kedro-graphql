import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
import dash
from components.dataset_card import dataset_card
import json

# the style arguments for the sidebar. We use position:fixed and a fixed width
DATA_CATALOG_STYLE = {
    "position": "fixed",
    "top": 0,
    "right": 0,
    "padding": "2rem 1rem",
}


@callback(
    Output("offcanvas", "is_open"),
    Input("open-offcanvas", "n_clicks"),
    [State("offcanvas", "is_open")],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def toggle_offcanvas(n1, is_open):
    if n1:
        return not is_open
    return is_open

@callback(Output("output", "children"), 
          [Input("input", "value"), Input("datasets", "children")],
          prevent_initial_call=True,
          suppress_callback_exceptions=True)
def output_text(value, children):
    print(value, children)
    return value

def data_catalog(title = "Data Catalog", pipeline_id = None, description = "A simple pipeline card layout with navigation links"):
    return html.Div(
        [
            dbc.Button("Open Data Catalog", 
                       id="open-offcanvas", 
                       n_clicks=0,
                       color="primary",
                       outline=True,
                       style = DATA_CATALOG_STYLE),
            dbc.Offcanvas(
                [
                    html.P(
                        f"Pipeline ID: {pipeline_id}"
                    ),
                    html.H5("Datasets"),
                    dbc.Input(id="input", placeholder="Type something...", type="text"),
                    html.Div(id="datasets", children = [
                        dataset_card(name="example00", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                        dataset_card(name="example01", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                        dataset_card(name="example02", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                        dataset_card(name="example03", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                        dataset_card(name="example04", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                        dataset_card(name="example05", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                        dataset_card(name="example06", config=json.dumps({"filepath": "s3://example.csv"}, sort_keys = True, indent = 2)),
                    ]
                )
                ],
                id="offcanvas",
                title="Data Catalog",
                placement="end",
                is_open=False,
                scrollable=True
            ),
        ]
    )
    ##return  html.Div(
    ##    [
    ##        dbc.Button(
    ##            "Data Catalog",
    ##            id="hover-target",
    ##            color="danger",
    ##            className="me-1",
    ##            n_clicks=0,
    ##        ),
    ##        dbc.Popover(
    ##            [
    ##                dbc.PopoverHeader("Parameters"),
    ##                dbc.PopoverBody("And here's some amazing content. Cool!"),
    ##                dbc.PopoverHeader("Datasets"),
    ##                dbc.PopoverBody(
    ##                    [
    ##                        dataset_card(name="example", config="")
    ##                    ]
    ##                ),
    ##            ],
    ##            target="hover-target",
    ##            body=True,
    ##            trigger="hover",
    ##            placement="bottom"
    ##        ),
    ##    ],
    ##    style=DATA_CATALOG_STYLE,
    ##)