import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash
from components.dataset_card import dataset_card
import json

import pandas as pd

df = pd.read_csv("src/kedro_graphql/ui/assets/example-data-catalog.csv")


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
    suppress_callback_exceptions=True
)
def toggle_offcanvas(n1, is_open):
    if n1:
        return not is_open
    return is_open

@callback(Output("output", "children"), [Input("input", "value"), Input("datasets", "children")])
def output_text(value):
    print(value, children)
    return value

def data_catalog_table(title = "Data Catalog", pipeline_id = None, description = "A simple pipeline card layout with navigation links"):
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
                    html.Div(id="datasets", children = [
                        dash_table.DataTable(
                            id='datatable-interactivity',
                            columns=[
                                {"name": i, "id": i, "deletable": False, "selectable": False} for i in df.columns
                            ],
                            data=df.to_dict('records'),
                            filter_action="native",
                            sort_action="native",
                            sort_mode="multi",
                            #selected_columns=[],
                            #selected_rows=[],
                            page_action="native",
                            #page_current= 0,
                            #page_size= 10,
                            style_data={
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            },
                        ),
                        html.Div(id='datatable-interactivity-container')
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

    
    
    html.Div([

    ]) 