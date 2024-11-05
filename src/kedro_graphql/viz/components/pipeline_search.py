## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import datetime as dt
import numpy as np
#from kedro_graphql.client import KedroGraphqlClient
pn.extension('tabulator')

class PipelineSearch(pn.viewable.Viewer):
  
    def navigate(self, event, df):
            ## event.column and event.row are accessible
            print("EVENT", event)
            if event.column == "Open":
                pn.state.location.pathname = "/pipelines/data/" + df.loc[event.row, "name"]
                pn.state.location.search = "?id=" + df.loc[event.row, "id"]
                pn.state.location.reload = True

    def __panel__(self):

        #forms = self._get_gql_forms()
        
        ## logic to build form here

        ## an example

        df = pd.DataFrame({
            'name': ["example00", "example01", "example00"],
            'id': ["0000000000001", "0000000000002", "0000000000003"],
            'status': ['RUNNING', "SUCCESS" , "FAILED"],
            'created': [dt.date(2019, 1, 1), dt.date(2020, 1, 1), dt.date(2020, 1, 10)],
            'tag:submitted by': ["username", "username", "username"],
        }, index=[0, 1, 2])
 
        df_widget = pn.widgets.Tabulator(df, 
                                         buttons={'Open': "<i class='fa fa-folder-open'></i>"}, 
                                         theme='materialize', 
                                         show_index=False)

        df_widget.on_click(
            lambda e: self.navigate(e, df)
        )
 
        
        return pn.Row(
            pn.Card("Search for a pipeline", 
                    pn.Row(
                      pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
                      pn.widgets.Button(name='Search', button_type='success'), 
                    ),
                    pn.Row(
                      df_widget
                    ),
                    sizing_mode = "stretch_width",
                    title='Search'),
        )
