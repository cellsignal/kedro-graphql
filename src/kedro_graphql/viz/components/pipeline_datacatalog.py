## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import datetime as dt
import numpy as np
#from kedro_graphql.viz.client import KedroGraphqlClient
from kedro_graphql.models import Pipeline
import json
import strawberry

pn.extension('tabulator')


class PipelineDataCatalog(pn.viewable.Viewer):
    id = param.String()



    def create_example_pipeline(self):
        input_dict = {"type": "text.TextDataset", "filepath": "/home/seanlandry/dev/kgql-client/kedro-graphql/data/01_raw/text_in.txt"}
        output_dict = {"type": "text.TextDataset", "filepath": "/home/seanlandry/dev/kgql-client/kedro-graphql/data/02_intermediate/text_out.txt"}
        
        ## PipelineInput object
        return Pipeline(**{
                          "name": "example00",
                          "data_catalog":[{"name": "text_in", "config": json.dumps(input_dict)},
                                          {"name": "text_out", "config": json.dumps(output_dict)}],
                          "parameters": [{"name":"example", "value":"hello"},
                                         {"name": "duration", "value": "3", "type": "FLOAT"}],
                          "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                         })

    #def navigate(self, event, df):
    #        ## event.column and event.row are accessible
    #        print("EVENT", event)
    #        if event.column == "Open":
    #            pn.state.location.pathname = "/pipelines/data/" + df.loc[event.row, "name"]
    #            pn.state.location.search = "?id=" + df.loc[event.row, "id"]
    #            pn.state.location.reload = True
    
    ##async def build_terminal(self):
    ##    client = KedroGraphqlClient()
    ##    yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

    ##    terminal =  pn.widgets.Terminal(
    ##        "Welcome to the Panel Terminal!\nI'm based on xterm.js\n\n",
    ##        options={"cursorBlink": True}, 
    ##        sizing_mode='stretch_width'
    ##    )
    ##    terminal.clear()
    ##    yield terminal
    ##    async for message in client.pipelineLogs(self.id):
    ##         terminal.write(message.time + " " + message.message + "\n")
            
    def __panel__(self):

        p = self.create_example_pipeline()
        param_df = pd.DataFrame({
                    'name': [i["name"] for i in p.parameters],
                    'value': [i["value"] for i in p.parameters],
                }, index=[i for i in range(len(p.parameters))])
        
        param_widget = pn.widgets.Tabulator(param_df,
                                         disabled=True,
                                         theme='materialize',
                                         show_index=False)

        ds_df = pd.DataFrame({
                    'name': [i["name"] for i in p.data_catalog],
                    'type': [json.loads(i["config"])["type"] for i in p.data_catalog],
                }, index=[i for i in range(len(p.data_catalog))])

        ds_widget = pn.widgets.Tabulator(ds_df, 
                                         buttons={'Download': "<i class='fa fa-download'></i>"}, 
                                         theme='materialize',
                                         show_index=False)



        return pn.Column(pn.Row(
                      "# Parameters",
                    ),
                    pn.Row(
                      param_widget,
                    ),
                    pn.Row(
                      "# Datasets",
                    ),
                    pn.Row(
                      ds_widget,
                    ),
 
                )
