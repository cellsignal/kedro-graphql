# some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import json
from kedro_graphql.models import Pipeline

pn.extension('ace', 'jsoneditor')
pn.extension('tabulator', css_files=[
             "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])


class PipelineDetail(pn.viewable.Viewer):
    pipeline = param.ClassSelector(class_=Pipeline)

    async def build_detail(self, raw):
        """Builds the detail view for the pipeline, showing its parameters, tags, data catalog, and status.

        TO DO:
            - Implement a more user-friendly way to view and interact with the pipeline's data catalog.
            - Support for "batch" view. View child pipelines or parent pipelines if applicable.

        Args:
            raw (pn.widgets.CheckButtonGroup): A widget to toggle between raw JSON view and structured view.
        Yields:
            pn.Row: A row containing the detail view of the pipeline.
        """
        if "json" in raw:
            yield pn.Row(
                pn.widgets.JSONEditor(
                    value=self.pipeline.encode(encoder="dict"),
                    mode="view",
                    width=600
                )
            )
        else:
            if self.pipeline.parameters:
                param_df = pd.DataFrame({
                    'name': [i.name for i in self.pipeline.parameters],
                    'value': [i.value for i in self.pipeline.parameters],
                }, index=[i for i in range(len(self.pipeline.parameters))])
            else:
                param_df = pd.DataFrame({
                    'name': [],
                    'value': [],
                }, index=[])

            param_widget = pn.widgets.Tabulator(
                param_df,
                disabled=True,
                theme='materialize',
                show_index=False
            )

            if self.pipeline.tags:
                tags_df = pd.DataFrame({
                    'key': [i.key for i in self.pipeline.tags],
                    'value': [i.value for i in self.pipeline.tags],
                }, index=[i for i in range(len(self.pipeline.tags))])
            else:
                tags_df = pd.DataFrame({'key': [], 'value': []})

            tags_widget = pn.widgets.Tabulator(
                tags_df,
                disabled=True,
                theme='materialize',
                show_index=False
            )

            if self.pipeline.data_catalog:
                ds_df = pd.DataFrame({
                    'name': [i.name for i in self.pipeline.data_catalog],
                    'type': [json.loads(i.config)["type"] for i in self.pipeline.data_catalog],
                }, index=[i for i in range(len(self.pipeline.data_catalog))])
            else:
                # backwards compatibility, will be deprecated
                ds_df = pd.DataFrame({
                    'name': [i.name for i in self.pipeline.inputs] + [i.name for i in self.pipeline.outputs],
                    'type': [i.type for i in self.pipeline.inputs] + [i.type for i in self.pipeline.outputs],
                }, index=[i for i in range(len(self.pipeline.inputs) + len(self.pipeline.outputs))])

            ds_widget = pn.widgets.Tabulator(
                ds_df,
                disabled=True,
                buttons={'Download': "<i class='fa fa-download'></i>"},
                theme='materialize',
                show_index=False
            )

            # in the future this will be a list of PipelineStatus objects
            # for now we grab each attribute from Pipeline object

            cols = [
                "state", "task_id", "task_name", "task_args", "task_kwargs",
                "task_request", "task_excpetion", "task_traceback", "task_einfo", "task_self.pipeline"
            ]
            values = self.pipeline.encode(encoder="dict")["status"]

            status_df = pd.DataFrame(
                values,
                columns=cols,
                index=[i for i in range(len(values))]
            )

            status_widget = pn.widgets.Tabulator(
                status_df,
                disabled=True,
                theme='materialize',
                layout='fit_columns',
                show_index=False
            )

            yield pn.Column(
                pn.Row(
                    pn.Card(
                        tags_widget,
                        title="Tags",
                        sizing_mode="stretch_width"
                    )
                ),
                pn.Row(
                    pn.Card(
                        param_widget,
                        title="Parameters",
                        sizing_mode="stretch_width"
                    )
                ),
                pn.Row(
                    pn.Card(
                        ds_widget,
                        title="Data Catalog",
                        sizing_mode="stretch_width"
                    )
                ),
                pn.Row(
                    pn.Card(
                        status_widget,
                        title="Runs",
                        sizing_mode="stretch_width"
                    )
                )
            )

    def __panel__(self):
        raw = pn.widgets.CheckButtonGroup(name='JSON', value=[], options=["json"])
        detail = pn.bind(self.build_detail, raw)
        return pn.Column(
            pn.Row(raw),
            pn.Row(detail),
            sizing_mode="stretch_width"
        )
