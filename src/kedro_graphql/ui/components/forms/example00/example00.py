import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
import dash
import json
import datetime
from dateutil import parser
from kedro_graphql.ui.components.form_submit import form_submit
from urllib.parse import quote_plus

from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader("kedro_graphql.ui.components.forms.example00"),
    autoescape=select_autoescape()
)

@callback(
    Output("pipeline-form-template", "children"),
    Input("input-duration", "value"),
    State("input-timestamp", "value"),
    suppress_callback_exceptions=True,
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
    template = env.get_template("template.json")
    catalog = template.render(parameters)
    return catalog

@callback(
    Output("pipeline-form-submit-resp", "data"),
    Input("pipeline-form-submit", "n_clicks"),
    State("pipeline-form-template", "children"),
    suppress_callback_exceptions=True,
)
def submit(value, template):
    
    if not value:
        return None
    else:
        ## need to add checks for errors
        resp = form_submit(json.loads(template))
        return resp

@callback(
    Output("url", "href", allow_duplicate=True),
    Input("pipeline-form-submit-resp", "modified_timestamp"),
    State("pipeline-form-submit-resp", "data"),
    prevent_initial_call=True,
)
def navigate(timestamp, pipeline):
    print("TIMESTAMP", timestamp)
    if not pipeline:
        return dash.no_update
    else:
        return f"/run/progress?pipeline="+quote_plus(json.dumps(pipeline))


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
                            dbc.Button("Submit", id="pipeline-form-submit", color="primary", className="mr-1"),
                            html.Div(id="pipeline-form-template"),
                            dcc.Store(id="pipeline-form-submit-resp")
                        ]
                    )
                ]
            )
        ]
    ) 
