## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import datetime as dt
import numpy as np
#from kedro_graphql.client import KedroGraphqlClient
pn.extension('tabulator')

class PipelineSearch(pn.viewable.Viewer):
    #client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)

    def __panel__(self):

        #forms = self._get_gql_forms()
        
        ## logic to build form here

        ## an example
        df = pd.DataFrame({
            'int': [1, 2, 3],
            'float': [3.14, 6.28, 9.42],
            'str': ['A', 'B', 'C'],
            'bool': [True, False, True],
            'date': [dt.date(2019, 1, 1), dt.date(2020, 1, 1), dt.date(2020, 1, 10)],
            'datetime': [dt.datetime(2019, 1, 1, 10), dt.datetime(2020, 1, 1, 12), dt.datetime(2020, 1, 10, 13)]
        }, index=[1, 2, 3])
        
        
        df_widget = pn.widgets.Tabulator(df, buttons={'Open': "<i class='fa fa-folder-open'></i>"})
        
        return pn.Row(
            pn.Card("Search for a pipeline", 
                    pn.Row(
                      pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
                    ),
                    pn.Row(
                      df_widget
                    ),
                    pn.Row(
                      pn.widgets.Button(name='Open', button_type='success'), 
                    ),
                    sizing_mode = "stretch_width",
                    title='Search'),
        )
