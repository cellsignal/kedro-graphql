
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html, callback


callback(
    [Output("progress", "value"), Output("progress", "label")],
    [Input("progress-interval", "n_intervals")],
    suppress_callback_exceptions=True
)
def update_progress(n):
    # check progress of some background process, in this example we'll just
    # use n_intervals constrained to be in 0-100
    progress = min(n % 110, 100)
    # only add text after 5% progress to ensure text isn't squashed too much
    return progress, f"{progress} %" if progress >= 5 else ""

def run_progress(pipeline_name =None, description = "A simple pipeline card layout with navigation links"):
    return html.Div(
        [
            dcc.Interval(id="progress-interval", n_intervals=0, interval=500),
            dbc.Progress(id="progress"),
        ]
    )
