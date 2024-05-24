import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
import dash
import json
import datetime
from dateutil import parser

from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader("kedro_graphql.ui.components.forms.example00"),
    autoescape=select_autoescape()
)

@callback(
    Output("pipeline-form-template", "children"),
    Input("input-duration", "value"),
    State("input-timestamp", "value"),
)
def update_template(duration, timestamp):
    timestamp = parser.parse(timestamp)
    parameters = {
                    "timestamp": timestamp,
                    "year": timestamp.year,
                    "month": timestamp.month,
                    "day": timestamp.day,
                    "duration": duration
                 }
    template = env.get_template("catalog.json")
    catalog = template.render(parameters)
    return catalog



def load(pipeline_template = {}):

    timestamp = datetime.datetime.now().isoformat()

    return dbc.Form(id="pipeline-form", children =
        [
            dbc.Card(
                [   
                    dbc.CardBody(
                        [
                            html.H4("Parameters", className="card-title"),
                            html.P(
                                "Enter parameters for the pipeline",
                                className="card-text",
                            ),
                            dbc.Row(
                               [
                                   dbc.Label("Timestamp", html_for="input-timestamp"),
                                   dbc.Col(
                                       dbc.Input(
                                           type="text", id="input-timestamp", value=timestamp, disabled=True
                                       ),
                                       width=12,
                                   ),
                                   dbc.Label("Duration", html_for="input-duration"),
                                   dbc.Col(
                                       [
                                           dbc.Input(
                                               type="text", id="input-duration", placeholder="3"
                                           ),
                                       ],
                                       width=12,
                                   ),
                               ],
                               className="mb-3"
                            ),
                            dbc.Button("Submit"),
                            html.Div(id="pipeline-form-template")
                            #html.Div(id="pipeline-form-template", style = {"display": "none"})
                        ]
                    )
                ]
            )
        ]
    ) 
