import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
import dash
import json

from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader("kedro_graphql.ui.components.forms.example00"),
    autoescape=select_autoescape()
)



def parameter_input(parameter):
    return dbc.Row(
        [
            dbc.Label(parameter["name"], html_for=f"{parameter['name']}-row"),
            dbc.Col(
                dbc.Input(
                    type="text", id=f"{parameter['name']}-row", placeholder=parameter["value"]
                ),
                width=12,
            ),
        ],
        className="mb-3",
    )


def parameters_input(parameters):
    return dbc.Card(
        [   
            dbc.CardBody(
                [
                    html.H4("Parameters", className="card-title"),
                    html.P(
                        "Enter parameters for the pipeline",
                        className="card-text",
                    ),
                    html.Div(
                        [parameter_input(parameter) for parameter in parameters]
                    )
                ]
            )
        ]
    )


def dataset_input(dataset):
    ## needed for backwards compatibility
    if dataset.get("config", None):
        return dbc.Row(
            [
                dbc.Label(dataset["name"], html_for=f"{dataset['name']}-row"),
                dbc.Col(
                    dbc.Input(
                        type="text", id=f"{dataset['name']}-row", placeholder=dataset["config"]
                    ),
                    width=10,
                ),
            ],
            className="mb-3",
        )
    else:
        return dbc.Row(
            [
                dbc.Label(dataset["name"], html_for=f"{dataset['name']}-row"),
                dbc.Col(
                    [dbc.Input(type="text", id=f"input-{dataset['name']}-{k}", placeholder=k) for k,v in dataset.items() if k != "name"],
                    width=12,
                ),
            ],
            className="mb-3",
        )

def datasets_input(datasets, title = "Input Datasets"):
    return dbc.Card(
        [   
            dbc.CardBody(
                [
                    html.H4(title, className="card-title"),
                    html.P(
                        "Enter input datasets for the pipeline",
                        className="card-text",
                    ),
                    html.Div(
                        [dataset_input(dataset) for dataset in datasets]
                    )
                ]
            )
        ]
    )


def load(pipeline_template = {}):
    return dbc.Form(id="pipeline-form", children =
        [
             parameters_input(pipeline_template["parameters"]), 
             datasets_input(pipeline_template["inputs"], title = "Input Datasets"), 
             datasets_input(pipeline_template["outputs"], title = "Output Datasets"),
             html.Div(id="pipeline-template-original", children = [json.dumps(pipeline_template)], style={'display': 'none'}),
             html.Div(id="pipeline-template-filled", children = [], style={'display': 'none'})

        ]
    ) 
