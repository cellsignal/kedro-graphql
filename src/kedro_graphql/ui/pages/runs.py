from dash import html
import dash
dash.register_page(__name__)

def layout(**kwargs):
    return html.Div([
        html.H1('This is our Runs page'),
        html.Div('This is our Runs page content.'),
    ])