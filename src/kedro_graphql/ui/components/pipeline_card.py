import dash_bootstrap_components as dbc
from dash import html, dcc
import dash

def pipeline_card(title = "Pipeline", description = "A simple pipeline card layout with navigation links"):
    return dbc.Card(
        [
            dbc.CardImg(src=dash.get_asset_url("pipeline.svg"), top=True, style = {"height": "100px"}),
            dbc.CardBody(
                [
                    html.H4(title, className="card-title"),
                    html.P(
                        dcc.Markdown(description),
                        className="card-text",
                    ),
                    dbc.Button("Run", color="primary", href="/run/submit/"+title),
                ]
            ),
        ],
    )