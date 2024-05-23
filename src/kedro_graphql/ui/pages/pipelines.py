from dash import html, Input, Output, callback
import dash
import requests
from components.pipeline_card import pipeline_card
import dash_bootstrap_components as dbc


dash.register_page(__name__)

def layout(**kwargs):
    return html.Div([
        html.H1('Pipelines'),
        html.Div(id="pipelines")
    ])

@callback(
    Output(component_id='pipelines', component_property='children'),
    Input(component_id='pipelines', component_property='children'),
    suppress_callback_exceptions=True
)
def get_pipelines(input_value):
    url = "http://localhost:5000/graphql"
    query = """
    {
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
    response = requests.post(url=url, json={"query": query}) 
    print("response status code: ", response.status_code) 
    if response.status_code == 200: 
        data = response.json()
        return dbc.Row([dbc.Col(pipeline_card(title = pipeline["name"], description = pipeline["describe"]), md="4") for pipeline in data["data"]["pipelineTemplates"]["pipelineTemplates"]])

