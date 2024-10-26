## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import datetime as dt
import numpy as np
#from kedro_graphql.client import KedroGraphqlClient
pn.extension('tabulator')

class PipelineMonitor(pn.viewable.Viewer):
    #client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    pipeline_name = param.String()

    def __panel__(self):

        #forms = self._get_gql_forms()
        
        ## logic to build form here

        ## an example
        df = pd.DataFrame({
            'int': [1],
            'float': [3.14],
            'str': ['A'],
            'bool': [True],
            'date': [dt.date(2019, 1, 1)],
            'datetime': [dt.datetime(2019, 1, 1, 10)]
        }, index=[1])
        
        
        df_widget = pn.widgets.Tabulator(df, buttons={'Open': "<i class='fa fa-folder-open'></i>"})
        terminal =  pn.widgets.Terminal(
            "Welcome to the Panel Terminal!\nI'm based on xterm.js\n\n",
            options={"cursorBlink": True},
            height=300, sizing_mode='stretch_width'
        )
    
        terminal.write("kedro log messages here")
        
        return pn.Row(
            pn.Card(self.pipeline_name, 
                    pn.Row(
                      df_widget
                    ),
                    pn.Row(
                      terminal 
                    ),
                    sizing_mode = "stretch_width",
                    title="Monitor"),
        )
