from dash import html, callback, Input, Output
import dash
from components.run_progress import run_progress

dash.register_page(__name__, path_template="/run/progress/<pipeline_id>")

def layout(pipeline_id=None, **kwargs):
    return html.Div([
        html.H1(f"Run: {pipeline_id}"),
        html.Div(id="pipeline-progress"),
    ])


@callback(
    Output(component_id='pipeline-progress', component_property='children'),
    Input(component_id='pipeline-progress', component_property='children'),
    suppress_callback_exceptions=True
)
def load_progress(input_value):
    return run_progress()