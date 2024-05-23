import dash_bootstrap_components as dbc
from dash import html, dcc
import dash

def dataset_card(name = "Pipeline", config = "A simple pipeline card layout with navigation links"):
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(name, className="card-title"),
                    ##html.H6(
                    ##    "config:",
                    ##    className="card-text",
                    ##),
                    ##html.P(
                    ##    config,
                    ##    className="card-text",
                    ##),
                    dbc.Button("Open", color="primary"),
                ]
            ),
        ],
    )