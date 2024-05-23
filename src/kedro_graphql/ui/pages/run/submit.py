from dash import html, callback, Input, Output
import dash
from components.form_loader import form_loader

dash.register_page(__name__, path_template="/run/submit/<pipeline_name>")

def layout(pipeline_name=None, **kwargs):
    return html.Div([
        html.H1(f"Run: {pipeline_name}"),
        html.Div(id="pipeline-submit"),
    ])


@callback(
    Output(component_id='pipeline-submit', component_property='children'),
    Input(component_id='pipeline-submit', component_property='children'),
    suppress_callback_exceptions=True
)
def load_form(input_value):
    return form_loader()