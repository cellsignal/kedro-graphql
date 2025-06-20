import panel as pn
import param
import asyncio
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import Pipeline, PipelineInput, ParameterInput, DataSetInput, TagInput, PipelineInputStatus, PipelineSlice

pn.extension('modal')
pn.extension(notifications=True)


class PipelineRetry(pn.viewable.Viewer):
    """A component that retries execution of a Kedro pipeline or a slice of it.

    Attributes:
        pipeline (Pipeline): The Kedro pipeline to retry.
        client (KedroGraphqlClient): The client used to interact with the Kedro GraphQL API.
    """

    pipeline = param.ClassSelector(class_=Pipeline)
    client = param.ClassSelector(class_=KedroGraphqlClient)

    def __init__(self, **params):
        super().__init__(**params)

        pn.state.notifications.position = 'top-center'

        self.select = pn.widgets.Select(
            name='Select retry strategy',
            options=['Whole', 'Slice'],
            value='Whole'
        )

        self.only_missing = pn.widgets.Checkbox(name='Only Missing')

        self.slice_inputs = {
            "tags": pn.widgets.TextInput(
                placeholder=f"e.g. tag1,tag2",
                name="Tags",
                sizing_mode="stretch_width"
            ),
            "from_nodes": pn.widgets.TextInput(
                placeholder="e.g. node_name1,node_name2",
                name="From Nodes",
                sizing_mode="stretch_width"
            ),
            "to_nodes": pn.widgets.TextInput(
                placeholder="e.g. node_name3,node_name4",
                name="To Nodes",
                sizing_mode="stretch_width"
            ),
            "node_names": pn.widgets.TextInput(
                placeholder="e.g. node_name5,node_name6",
                name="Node Names",
                sizing_mode="stretch_width"
            ),
            "from_inputs": pn.widgets.TextInput(
                placeholder="e.g. input1,input2",
                name="From Inputs",
                sizing_mode="stretch_width"
            ),
            "to_outputs": pn.widgets.TextInput(
                placeholder="e.g. output1,output2",
                name="To Outputs",
                sizing_mode="stretch_width"
            ),
            "node_namespace": pn.widgets.TextInput(
                placeholder="e.g. namespace1,namespace2",
                name="Node Namespace",
                sizing_mode="stretch_width"
            ),
        }

        yes_button = pn.widgets.Button(name="Yes", button_type="primary")
        cancel_button = pn.widgets.Button(name="Cancel")
        yes_button.on_click(lambda e: asyncio.create_task(self.pipeline_run()))
        cancel_button.on_click(lambda e: self.modal.hide())

        self.modal = pn.Modal(
            pn.Column(
                pn.pane.Markdown("### Are you sure you want to retry? This could overwrite any previous data."),
                pn.Row(yes_button, cancel_button)
            ),
            name="Confirm Retry",
            margin=20,
            width=400,
        )

    async def build_card(self, strategy):
        """ Builds a card for retrying the pipeline or a slice of it based on the selected strategy.

        Args:
            strategy (str): The retry strategy selected by the user, either 'Whole' or 'Slice'.

        Yields:
            pn.Card: A card containing the retry options and a button to trigger the retry.

        """
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        if strategy == 'Whole':
            retry_all_button = pn.widgets.Button(
                name="Retry Whole Pipeline", button_type="success", sizing_mode="stretch_width",
            )
            retry_all_button.on_click(lambda event: self.modal.toggle())
            yield pn.Card(
                self.select,
                retry_all_button,
                title="Retry Whole Pipeline",
                width=400,
            )
        else:

            retry_slice_button = pn.widgets.Button(
                name="Retry Pipeline Slice", button_type="success", sizing_mode="stretch_width",
            )
            retry_slice_button.on_click(lambda event: self.modal.toggle())
            yield pn.Card(
                self.select,
                pn.Row(self.slice_inputs["tags"], pn.widgets.TooltipIcon(value="Construct the pipeline using only nodes which have this tag attached.")),
                pn.Row(self.slice_inputs["from_nodes"], pn.widgets.TooltipIcon(value="A list of node names which should be used as a starting point.")),
                pn.Row(self.slice_inputs["to_nodes"], pn.widgets.TooltipIcon(value="A list of node names which should be used as an end point.")),
                pn.Row(self.slice_inputs["node_names"], pn.widgets.TooltipIcon(value="Run only nodes with specified names.")),
                pn.Row(self.slice_inputs["from_inputs"], pn.widgets.TooltipIcon(value="A list of dataset names which should be used as a starting point.")),
                pn.Row(self.slice_inputs["to_outputs"], pn.widgets.TooltipIcon(value="A list of dataset names which should be used as an end point.")),
                pn.Row(self.slice_inputs["node_namespace"], pn.widgets.TooltipIcon(value="Name of the node namespace to run.")),
                pn.Row(self.only_missing, pn.widgets.TooltipIcon(value="Run only the missing outputs.")),
                retry_slice_button,
                title="Retry a Slice",
                width=400
            )

    async def pipeline_run(self):
        """Run the pipeline based on the selected retry strategy."""

        self.modal.hide()

        try:
            if self.select.value == 'Whole':
                pipeline_input = PipelineInput(name=self.pipeline.name,
                                               parameters=[
                                                   ParameterInput(
                                                       name=param.name, value=param.value, type=param.type.name)
                                                   for param in self.pipeline.parameters]
                                               if self.pipeline.parameters else [],
                                               data_catalog=[DataSetInput(name=ds.name, config=ds.config)
                                                             for ds in self.pipeline.data_catalog]
                                               if self.pipeline.data_catalog else [],
                                               tags=[TagInput(key=tag.key, value=tag.value) for tag in self.pipeline.tags]
                                               if self.pipeline.tags else [], runner=self.pipeline.status[-1].runner,
                                               state=PipelineInputStatus.READY)
            else:
                slices = []
                for key, field in self.slice_inputs.items():
                    if field.value.strip():
                        slices.append(
                            PipelineSlice(
                                slice=key.upper(),
                                args=[item.strip() for item in field.value.split(',')]))

                pipeline_input = PipelineInput(name=self.pipeline.name,
                                               parameters=[
                                                   ParameterInput(
                                                       name=param.name, value=param.value, type=param.type.name)
                                                   for param in self.pipeline.parameters]
                                               if self.pipeline.parameters else [],
                                               data_catalog=[DataSetInput(name=ds.name, config=ds.config)
                                                             for ds in self.pipeline.data_catalog]
                                               if self.pipeline.data_catalog else [],
                                               tags=[TagInput(key=tag.key, value=tag.value) for tag in self.pipeline.tags]
                                               if self.pipeline.tags else [], runner=self.pipeline.status[-1].runner,
                                               state=PipelineInputStatus.READY, slices=slices,
                                               only_missing=self.only_missing.value)

            await self.client.update_pipeline(id=self.pipeline.id, pipeline_input=pipeline_input)

        except Exception as e:
            pn.state.notifications.error(

                f"Failed to trigger {self.select.value.lower()} retry for {self.pipeline.name}: {str(e)}",
                duration=10000
            )
            return

        pn.state.notifications.success(
            f'Successfully triggered {self.select.value.lower()} retry for {self.pipeline.name}', duration=10000)

    def __panel__(self):

        return pn.Column(
            pn.bind(self.build_card, self.select),
            self.modal,
        )
