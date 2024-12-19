## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import datetime as dt
import numpy as np
from kedro_graphql.viz.client import KedroGraphqlClient
import json
from fastapi.encoders import jsonable_encoder

pn.extension('tabulator', 'ace', 'jsoneditor')



class PipelineDetail(pn.viewable.Viewer):
    id = param.String(default = '')

    async def build_detail(self, raw):
        client = KedroGraphqlClient()
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        result = await client.readPipeline(self.id)
        ## NEED TO HANDLE BATCH VIEW
        ## MAYBE add Dataset browser for bulk select and download
        if "json" in raw:
            yield pn.Row(pn.widgets.JSONEditor(value=jsonable_encoder(result), mode = "view", width=600))
        else:
            param_df = pd.DataFrame({
                        'name': [i.name for i in result.parameters],
                        'value': [i.value for i in result.parameters],
                    }, index=[i for i in range(len(result.parameters))])
        
            param_widget = pn.widgets.Tabulator(param_df,
                                             disabled=True,
                                             theme='materialize',
                                             show_index=False)

            tags_df = pd.DataFrame({
                        'key': [i.key for i in result.tags],
                        'value': [i.value for i in result.tags],
                    }, index=[i for i in range(len(result.tags))])
        
            tags_widget = pn.widgets.Tabulator(tags_df,
                                             disabled=True,
                                             theme='materialize',
                                             show_index=False)


            ds_df = pd.DataFrame({
                        'name': [i.name for i in result.data_catalog],
                        'type': [json.loads(i.config)["type"] for i in result.data_catalog],
                    }, index=[i for i in range(len(result.data_catalog))])

            ds_widget = pn.widgets.Tabulator(ds_df, 
                                             buttons={'Download': "<i class='fa fa-download'></i>"}, 
                                             theme='materialize',
                                             show_index=False)


            ## in the future this be a list of PipelineStatus objects
            ## for now we grab each attribute from Pipeline object

            keys = ["status","task_id", "task_name", "task_args", "task_kwargs", "task_request","task_excpetion", "task_traceback", "task_einfo", "task_result"]
            values = [result.status, result.task_id, result.task_name, result.task_args, result.task_kwargs, result.task_request, result.task_exception, result.task_traceback, result.task_einfo, result.task_result]
            status_df = pd.DataFrame({
                        'key': keys,
                        'value': values,
                    }, index=[i for i in range(len(keys))])
        
            status_widget = pn.widgets.Tabulator(status_df,
                                             disabled=True,
                                             theme='materialize',
                                             show_index=False)



            yield pn.Column(
                        pn.Row(
                          "# Tags",
                        ),
                        pn.Row(
                            tags_widget, 
                        ),
                        pn.Row(
                          "# Parameters",
                        ),
                        pn.Row(
                          param_widget,
                        ),
                        pn.Row(
                          "# Data Catalog",
                        ),
                        pn.Row(
                          ds_widget,
                        ),
                        pn.Row(
                          "# Status",
                        ),
                        pn.Row(
                          status_widget,
                        )
                    )

            
    def __panel__(self):
        raw = pn.widgets.CheckButtonGroup(name='JSON', value=[], options=["json"])
        detail = pn.bind(self.build_detail, raw)
        return pn.Card(
            pn.Row(
                raw  
            ),
            pn.Row(
                detail
            ),
            sizing_mode = "stretch_width"
        )