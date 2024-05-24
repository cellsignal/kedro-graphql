from dash import html, Input, Output, callback
import dash
from components.pipeline_card import pipeline_template_card
import dash_bootstrap_components as dbc
from kedro_graphql.ui.client import client
from gql import gql

dash.register_page(__name__)

def layout(**kwargs):
    return html.Div([
        html.H1('Pipelines'),
        dbc.Container(id="pipelines", fluid = True)
    ])

@callback(
    Output(component_id='pipelines', component_property='children'),
    Input(component_id='pipelines', component_property='children'),
    suppress_callback_exceptions=True
)
def get_pipeline_templates(input_value):
    query = gql(
    """
    query getPipelineTemplates {
      pipelineTemplates(limit: 10) {
        pageMeta {
          nextCursor
        }
        pipelineTemplates {
          name
          describe
          inputs {
            name
            filepath
            type
          }
          nodes {
            name
            inputs
            outputs
            tags
          }
          outputs {
            filepath
            name
            type
          }
          parameters {
            name
            value
          }
        }
      }
    }
    """
    )

    result = client.execute(query)
    return dbc.Row([dbc.Col(pipeline_template_card(pipeline_template=template), md="4") for template in result["pipelineTemplates"]["pipelineTemplates"]])