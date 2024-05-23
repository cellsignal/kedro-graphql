import dash_bootstrap_components as dbc
from dash import html, dcc
import dash
import json
from urllib.parse import quote_plus

def pipeline_template_card(pipeline_template = {"name": "example", "describe": "An example pipeline card layout with navigation links"}):
    return dbc.Card(
        [
            dbc.CardImg(src=dash.get_asset_url("pipeline.svg"), top=True, style = {"height": "100px"}),
            dbc.CardBody(
                [
                    html.H4(pipeline_template["name"], className="card-title"),
                    html.P(
                        dcc.Markdown(pipeline_template["describe"]),
                        className="card-text",
                    ),
                    dbc.Button("Run", color="primary", href="/run/form?pipeline_template="+quote_plus(json.dumps(pipeline_template))),
                ]
            ),
        ],
    )