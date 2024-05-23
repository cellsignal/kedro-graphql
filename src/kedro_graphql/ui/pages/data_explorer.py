from dash import html, Input, Output, callback
import dash
import requests
from components.data_catalog_table import data_catalog_table
import dash_bootstrap_components as dbc


dash.register_page(__name__, path_template="/data_explorer/<pipeline_id>")

def layout(pipeline_id = None, **kwargs):
    return html.Div([
        html.H1('Data Explorer'),
        dbc.Container(id="data-explorer", fluid = True)
    ])

@callback(
    Output(component_id='data-explorer', component_property='children'),
    Input(component_id='data-explorer', component_property='children'),
    suppress_callback_exceptions=True
)
def get_pipeline(input_value):
    url = "http://localhost:5000/graphql"

    query = """
    { 
      pipeline(id: "664e9ee0d5ab14a983377321"){
        id
      }
    }
    """

    response = requests.post(url=url, json={"query": query}) 
    #print("response status code: ", response.status_code) 
    if response.status_code == 200: 
        data = response.json()["data"]
        return dbc.Row(dbc.Col(data_catalog_table(title = data["pipeline"]["id"], pipeline_id = data["pipeline"]["id"], description = data["pipeline"]["id"]), md="4"))

