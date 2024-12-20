## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import json
from fastapi.encoders import jsonable_encoder
from kedro_graphql.models import Pipeline

pn.extension('tabulator', 'ace', 'jsoneditor')



class PipelineDetail(pn.viewable.Viewer):
    pipeline = param.ClassSelector(class_=Pipeline)

    async def build_detail(self, raw):
        ## NEED TO HANDLE BATCH VIEW
        ## MAYBE add Dataset browser for bulk select and download
        if "json" in raw:
            yield pn.Row(pn.widgets.JSONEditor(value=jsonable_encoder(self.pipeline), mode = "view", width=600))
        else:
            param_df = pd.DataFrame({
                        'name': [i.name for i in self.pipeline.parameters],
                        'value': [i.value for i in self.pipeline.parameters],
                    }, index=[i for i in range(len(self.pipeline.parameters))])
        
            param_widget = pn.widgets.Tabulator(param_df,
                                             disabled=True,
                                             theme='materialize',
                                             show_index=False)

            tags_df = pd.DataFrame({
                        'key': [i.key for i in self.pipeline.tags],
                        'value': [i.value for i in self.pipeline.tags],
                    }, index=[i for i in range(len(self.pipeline.tags))])
        
            tags_widget = pn.widgets.Tabulator(tags_df,
                                             disabled=True,
                                             theme='materialize',
                                             show_index=False)


            ds_df = pd.DataFrame({
                        'name': [i.name for i in self.pipeline.data_catalog],
                        'type': [json.loads(i.config)["type"] for i in self.pipeline.data_catalog],
                    }, index=[i for i in range(len(self.pipeline.data_catalog))])

            ds_widget = pn.widgets.Tabulator(ds_df, 
                                             buttons={'Download': "<i class='fa fa-download'></i>"}, 
                                             theme='materialize',
                                             show_index=False)


            ## in the future this be a list of PipelineStatus objects
            ## for now we grab each attribute from Pipeline object

            keys = ["status","task_id", "task_name", "task_args", "task_kwargs", "task_request","task_excpetion", "task_traceback", "task_einfo", "task_self.pipeline"]
            values = [self.pipeline.status, self.pipeline.task_id, self.pipeline.task_name, self.pipeline.task_args, self.pipeline.task_kwargs, self.pipeline.task_request, self.pipeline.task_exception, self.pipeline.task_traceback, self.pipeline.task_einfo, self.pipeline.task_result]
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