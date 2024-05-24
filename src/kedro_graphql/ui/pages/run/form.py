from dash import html, callback, Input, Output
import dash
from components.form_loader import form_loader
import json
from urllib.parse import unquote
import dash_bootstrap_components as dbc
import importlib

forms = [importlib.import_module(f"kedro_graphql.ui.components.forms.example00.example00")]


dash.register_page(__name__, path_template="/run/form")

def layout(pipeline_template=None, **kwargs):
    pipeline_template = unquote(pipeline_template)
    return html.Div([
        html.H1("Run"),
        html.Div(id="pipeline-template", children = [pipeline_template], style={'display': 'none'}),
        html.Div(id="pipeline-form-container", children = []),
    ])


@callback(
    Output('pipeline-form-container', 'children'),
    Input('pipeline-template', 'children'),
    suppress_callback_exceptions=True
)
def load_form(input_value):
    return form_loader(pipeline_template=json.loads(input_value[0]))