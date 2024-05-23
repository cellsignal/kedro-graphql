from dash import html, callback, Input, Output
import dash
from components.progress_card import progress_card

dash.register_page(__name__, path_template="/run/progress/<pipeline_id>")

def layout(pipeline_id=None, **kwargs):
    return html.Div([
        html.H1(f"Run: {pipeline_id}"),
        html.Div(id="pipeline-progress"),
        progress_card()
    ])
