from dash_extensions.enrich import html, callback, Input, Output
from dash_extensions import WebSocket
import dash
from components.progress_card import progress_card
from urllib.parse import unquote, quote_plus
#from gql import gql
import json

dash.register_page(__name__, path_template="/run/progress")

def layout(pipeline=None, **kwargs):
    pipeline = json.loads(unquote(pipeline))
    query = """{
       	pipeline(id:"""+ '"' + str(pipeline["pipeline"]["id"]) + '"' + """) {
           id
           taskId
           status
           result
           timestamp
           traceback
         }
    }
    """
    
    return html.Div([
        html.H1(f"Run Progress"),
        html.Div(id="pipeline-progress", children = [json.dumps(pipeline)]),
        WebSocket(id="pipeline-progress-events-ws", url="ws://localhost:5000/graphql?subscription=" + quote_plus(query)),
        #WebSocket(id="pipeline-progress-events-ws", url="ws://localhost:5000/graphql"),
        html.Div(id="pipeline-progress-events"),
        #progress_card()
    ])


@callback(Output("pipeline-progress-events", "children"),
          Input("pipeline-progress-events-ws", "message"))
def update_events(message):
    return json.dumps(message)
