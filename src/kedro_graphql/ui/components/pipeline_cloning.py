import asyncio
import param
import panel as pn
import json
from copy import deepcopy
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import Pipeline, Tag, ParameterType, ParameterInput, DataSetInput, TagInput, PipelineInput, PipelineInputStatus

pn.extension('modal')
pn.extension(notifications=True)

SECTION_ITEM_STYLES = {
    'margin-top': 'auto',
    'margin-bottom': 'auto',
    'justify-content': 'left',
    'background-color': '#f0f0f0',
    'padding': '10px',
    'margin': '10px',
    'border-radius': '5px',
    'word-break': 'break-all',
}

class PipelineCloning(pn.viewable.Viewer):
    """
    A Panel component that clones a Kedro pipeline.

    Attributes:
        pipeline (Pipeline): The Kedro pipeline to retry.
        client (KedroGraphqlClient): The client used to interact with the Kedro GraphQL API.
    """

    pipeline = param.ClassSelector(class_=Pipeline)
    client = param.ClassSelector(class_=KedroGraphqlClient)

    def __init__(self, **params):
        super().__init__(**params)

        pn.state.notifications.position = 'top-center'
        
        if not self.pipeline or not self.client:
            self._content = pn.Column(
                pn.pane.Markdown("**Missing required parameters: `pipeline`, or `client`.**"),
                sizing_mode="stretch_width"
            )
        else:
            self.state = deepcopy(self.pipeline)
            
            # Show loading spinner until the dashboard is built
            self._content = pn.Column(
                pn.indicators.LoadingSpinner(value=True, width=50, height=50),
                pn.pane.Markdown("Fetching Data..."),
                sizing_mode='stretch_width'
            )
            
            # Ensures build after panel server is fully loaded to avoid race conditions
            pn.state.onload(lambda: asyncio.create_task(asyncio.to_thread(self.build_component)))
    
    def build_component(self):
        """Builds the pipeline cloning component with datasets, parameters, and tags sections."""
        self.datasets_section = self._create_datasets_section()
        self.parameters_section = self._create_parameters_section()
        self.tags_section = self._create_tags_section()

        stage_button = pn.widgets.Button(name="Clone & Stage", button_type="primary", width=200, height=50)
        run_button = pn.widgets.Button(name="Clone & Run", button_type="success", width=200, height=50)

        run_button.on_click(lambda event: asyncio.create_task(self.clone_pipeline(type="ready")))
        stage_button.on_click(lambda event: asyncio.create_task(self.clone_pipeline(type="staged")))

        self.view = pn.Column(
            self.datasets_section,
            self.parameters_section,
            self.tags_section,
            pn.Row(
                stage_button,
                run_button,
                styles={'margin-top': '25px'}
            ),
            margin=(10, 10),
            scroll=True
        )
        
        self._content[:] = pn.Column(
            pn.Card(
                self.view,
                title=f"Clone Pipeline: {self.pipeline.name}",
                sizing_mode="stretch_width"
            ),
            sizing_mode="stretch_width"
        )

    def _create_datasets_section(self):
        """Creates a section for editing datasets in the pipeline."""

        widgets = []
        if self.state.data_catalog:
            for dataset in self.state.data_catalog:
                try:
                    config = json.loads(dataset.config)
                    name = dataset.name
                    filepath = config.get("filepath", "")

                    edit_button = pn.widgets.Button(
                        name="Edit",
                        button_type="primary",
                        width=100,
                        styles={'margin-top': 'auto', 'margin-bottom': 'auto'}
                    )
                    modal = self._dataset_edit_modal(dataset, edit_button)

                    dataset_block = pn.Row(
                        edit_button,
                        pn.Column(
                            pn.pane.HTML(f"<b>Name</b>: {name}", styles={'font-size': '16px'}),
                            pn.pane.HTML(f"<b>Filepath</b>: {filepath}", styles={'font-size': '16px'}),
                            styles={'margin-top': 'auto', 'margin-bottom': 'auto'}
                        ),
                        modal,
                        styles=SECTION_ITEM_STYLES
                    )
                    widgets.append(dataset_block)
                except json.JSONDecodeError as e:
                    pn.state.notifications.error(
                        f"Failed to decode JSON for dataset {dataset.name}: {str(e)}",
                        duration=10000
                    )
                    continue

        return pn.Column(
            pn.pane.Markdown("## Datasets"),
            pn.FlexBox(*widgets) if widgets else pn.pane.Markdown("No datasets found."),
        )

    def _dataset_edit_modal(self, dataset, trigger):
        """Return modal for editing dataset configurations"""

        try:
            config = json.loads(dataset.config)
        except json.JSONDecodeError:
            self._show_error(f"Invalid configuration for dataset {dataset.name}")
            return pn.Modal("Error", "Invalid dataset configuration")

        original_path = config.get("filepath", "")
        filepath_input = pn.widgets.TextInput(name="Filepath", value=original_path)

        tag_inputs = []
        modal_items = [filepath_input, "### Dataset Tags"]
        if dataset.tags:
            for tag in dataset.tags:
                delete_button = pn.widgets.Button(name="Delete", button_type="danger", width=100)
                modal = self._delete_dataset_tag_modal(dataset, tag, delete_button)
                tag_key_input = pn.widgets.TextInput(name="Tag Key", value=tag.key)
                tag_value_input = pn.widgets.TextInput(name="Tag Value", value=tag.value)
                tag_inputs.append(pn.Row(delete_button, pn.Column(tag_key_input, tag_value_input), modal, styles={
                    'border': '1px solid #cccccc', 'padding': '10px', 'margin': '10px', 'border-radius': '5px'}))

            for row in tag_inputs:
                modal_items.extend([row])

        save_button = pn.widgets.Button(name="Save", button_type="success")
        cancel_button = pn.widgets.Button(name="Cancel")

        add_button = pn.widgets.Button(name="Add Tag", button_type="success", width=100)
        add_tag_modal = self._add_dataset_tag_modal(dataset, add_button)
        modal_items.append(pn.Row(add_button, add_tag_modal))
        modal_items.append(pn.Row(cancel_button, save_button, styles={'margin-top': '25px'}))

        modal = pn.Modal("### Edit Dataset", *modal_items)

        def open_modal(event):
            modal.show()

        def save(event):
            new_path = filepath_input.value.strip()
            if not new_path or new_path == original_path:
                pn.state.notifications.error("Filepath must be changed and not empty.", duration=10000)
                return

            config["filepath"] = new_path
            dataset.config = json.dumps(config)

            modal.hide()
            self.view[0] = self._create_datasets_section()

        def cancel(event):
            filepath_input.value = original_path
            modal.hide()

        trigger.on_click(open_modal)
        save_button.on_click(save)
        cancel_button.on_click(cancel)

        return modal

    def _delete_dataset_tag_modal(self, dataset, tag, trigger):
        """Return modal for deleting a dataset tag"""

        confirm_button = pn.widgets.Button(name="Confirm", button_type="danger")
        cancel_button = pn.widgets.Button(name="Cancel")

        modal = pn.Modal("### Delete Tag", "Are you sure you want to delete this tag?",
                         pn.Row(cancel_button, confirm_button))

        def open_modal(event):
            modal.show()

        def confirm(event):
            for i, t in enumerate(dataset.tags):
                if t.key == tag.key and t.value == tag.value:
                    del dataset.tags[i]
                    self.view[0] = self._create_datasets_section()
                    pn.state.notifications.success("Tag deleted successfully.", duration=10000)
                    break

            modal.hide()

        def cancel(event):
            modal.hide()

        trigger.on_click(open_modal)
        confirm_button.on_click(confirm)
        cancel_button.on_click(cancel)

        return modal

    def _add_dataset_tag_modal(self, dataset, trigger):
        """Return modal for adding a new tag to a dataset"""

        key_input = pn.widgets.TextInput(name="Key", placeholder="Enter tag key")
        value_input = pn.widgets.TextInput(name="Value", placeholder="Enter tag value")

        save_button = pn.widgets.Button(name="Save", button_type="success")
        cancel_button = pn.widgets.Button(name="Cancel")
        modal = pn.Modal("### Add Tag", key_input, value_input, pn.Row(cancel_button, save_button))

        def open_modal(event):
            modal.show()

        def save(event):
            new_key = key_input.value.strip()
            new_value = value_input.value.strip()
            if new_key and new_value:
                if dataset.tags:
                    dataset.tags.append(Tag(key=new_key, value=new_value))
                else:
                    dataset.tags = [Tag(key=new_key, value=new_value)]
            else:
                pn.state.notifications.error("Key or value cannot be empty.", duration=10000)

            modal.hide()
            self.view[0] = self._create_datasets_section()

        def cancel(event):
            key_input.value = ""
            value_input.value = ""
            modal.hide()

        trigger.on_click(open_modal)
        save_button.on_click(save)
        cancel_button.on_click(cancel)

        return modal

    def _create_parameters_section(self):
        """Creates a section for editing/deleting parameters in the pipeline."""

        widgets = []
        if self.state.parameters:
            for parameter in self.state.parameters:
                edit_button = pn.widgets.Button(name="Edit", button_type="primary", width=100, styles={
                    'margin-top': 'auto', 'margin-bottom': 'auto'})
                modal = self._param_edit_modal(parameter, edit_button)
                widgets.append(pn.Row(
                    edit_button,
                    pn.Column(pn.pane.HTML(f"<b>Name</b>: {parameter.name}", styles={'font-size': '16px'}),
                              pn.pane.HTML(f"<b>Value</b>: {parameter.value}", styles={'font-size': '16px'}),
                              pn.pane.HTML(f"<b>Type</b>: {parameter.type.value}", styles={'font-size': '16px'}), styles={
                        'margin-top': 'auto', 'margin-bottom': 'auto'}),
                    modal, styles=SECTION_ITEM_STYLES
                ))

        return pn.Column(
            pn.pane.Markdown("## Parameters"),
            pn.FlexBox(
                *widgets) if widgets else pn.pane.Markdown("No parameters found."),
        )

    def _param_edit_modal(self, parameter, trigger):
        """Return modal for editing a parameter's value and type"""

        value_input = pn.widgets.TextInput(name="Value", value=parameter.value)
        type_input = pn.widgets.Select(
            name="Type", options=["string", "float", "boolean", "integer"],
            value=parameter.type.value)

        save_button = pn.widgets.Button(name="Save", button_type="success")
        cancel_button = pn.widgets.Button(name="Cancel")
        modal = pn.Modal(f"### Edit Parameter '{parameter.name}'", value_input, type_input, pn.Row(
            cancel_button, save_button, styles={'margin-top': '25px'}))

        def open_modal(event):
            modal.show()

        def save(event):
            new_value = value_input.value.strip()
            new_type = type_input.value
            if new_value:
                parameter.value = new_value
                if new_type == "float":
                    parameter.type = ParameterType.FLOAT
                elif new_type == "boolean":
                    parameter.type = ParameterType.BOOLEAN
                elif new_type == "integer":
                    parameter.type = ParameterType.INTEGER
                else:
                    parameter.type = ParameterType.STRING
                modal.hide()
                self.view[1] = self._create_parameters_section()

            else:
                pn.state.notifications.error("Name, value or type cannot be empty.", duration=10000)

        def cancel(event):
            value_input.value = parameter.value
            type_input.value = parameter.type
            modal.hide()

        trigger.on_click(open_modal)
        save_button.on_click(save)
        cancel_button.on_click(cancel)

        return modal

    def _create_tags_section(self):
        """Creates a section for editing/deleting tags in the pipeline."""

        widgets = []
        if self.state.tags:
            for tag in self.state.tags:
                edit_button = pn.widgets.Button(name="Edit", button_type="primary", width=100)
                edit_tag_modal = self._tag_edit_modal(tag, edit_button)
                delete_button = pn.widgets.Button(name="Delete", button_type="danger", width=100)
                delete_tag_modal = self._pipeline_tag_delete_modal(tag, delete_button)
                widgets.append(
                    pn.Row(
                        pn.Column(edit_button, delete_button, styles={'margin-top': 'auto', 'margin-bottom': 'auto'}),
                        pn.Column(
                            pn.pane.HTML(f"<b>Key</b>: {tag.key}", styles={'font-size': '16px'}),
                            pn.pane.HTML(f"<b>Value</b>: {tag.value}", styles={'font-size': '16px'}),
                            styles={'margin-top': 'auto', 'margin-bottom': 'auto'}),
                        edit_tag_modal, delete_tag_modal,
                        styles=SECTION_ITEM_STYLES))

        add_button = pn.widgets.Button(name="Add", button_type="success", width=100,
                                       styles={'margin-top': 'auto', 'margin-bottom': 'auto'})
        widgets.append(pn.Row(add_button, styles=SECTION_ITEM_STYLES))
        add_tag_modal = self._add_tag_modal(add_button)

        return pn.Column(
            pn.pane.Markdown("## Pipeline Tags"),
            pn.FlexBox(*widgets),
            add_tag_modal
        )

    def _add_tag_modal(self, trigger):
        """Return modal for adding a new tag to the pipeline"""

        key_input = pn.widgets.TextInput(name="Key", placeholder="Enter tag key")
        value_input = pn.widgets.TextInput(name="Value", placeholder="Enter tag value")

        save_button = pn.widgets.Button(name="Save", button_type="success")
        cancel_button = pn.widgets.Button(name="Cancel")
        modal = pn.Modal("### Add Tag", key_input, value_input, pn.Row(cancel_button, save_button, styles={
            'margin-top': '25px'}))

        def open_modal(event):
            modal.show()

        def save(event):
            new_key = key_input.value.strip()
            new_value = value_input.value.strip()
            if new_key and new_value:
                self.state.tags.append(Tag(key=new_key, value=new_value))
                modal.hide()
                self.view[2] = self._create_tags_section()
            else:
                pn.state.notifications.error("Key or value cannot be empty.", duration=10000)

        def cancel(event):
            key_input.value = ""
            value_input.value = ""
            modal.hide()

        trigger.on_click(open_modal)
        save_button.on_click(save)
        cancel_button.on_click(cancel)

        return modal

    def _tag_edit_modal(self, tag, trigger):
        """Return modal for editing a tag's key and value"""

        key_input = pn.widgets.TextInput(name="Key", value=tag.key)
        value_input = pn.widgets.TextInput(name="Value", value=tag.value)

        save_button = pn.widgets.Button(name="Save", button_type="success")
        cancel_button = pn.widgets.Button(name="Cancel")
        modal = pn.Modal("### Edit Tag", key_input, value_input, pn.Row(cancel_button, save_button, styles={
            'margin-top': '25px'}))

        def open_modal(event):
            modal.show()

        def save(event):
            new_key = key_input.value.strip()
            new_value = value_input.value.strip()
            if new_key and new_value:
                tag.key = new_key
                tag.value = new_value
                modal.hide()
                self.view[2] = self._create_tags_section()
            else:
                pn.state.notifications.error("Key or value cannot be empty.", duration=10000)

        def cancel(event):
            key_input.value = tag.key
            value_input.value = tag.value
            modal.hide()

        trigger.on_click(open_modal)
        save_button.on_click(save)
        cancel_button.on_click(cancel)

        return modal

    def _pipeline_tag_delete_modal(self, tag, trigger):

        confirm_button = pn.widgets.Button(name="Confirm", button_type="danger")
        cancel_button = pn.widgets.Button(name="Cancel")

        modal = pn.Modal("### Delete Tag", "Are you sure you want to delete this tag?",
                         pn.Row(cancel_button, confirm_button))

        def open_modal(event):
            modal.show()

        def confirm(event):
            for i, t in enumerate(self.state.tags):
                if t.key == tag.key and t.value == tag.value:
                    del self.state.tags[i]
                    pn.state.notifications.success(
                        f"Pipeline Tag ({t.key}: {t.value}) deleted successfully.",
                        duration=10000)
                    break
            modal.hide()
            self.view[2] = self._create_tags_section()

        def cancel(event):
            modal.hide()

        trigger.on_click(open_modal)
        confirm_button.on_click(confirm)
        cancel_button.on_click(cancel)

        return modal

    async def clone_pipeline(self, type="staged"):
        """Clones the pipeline and stages or runs it based on the operation type.

        Args:
            type (str): The type of post-cloning operation, either "staged" or "ready".
        """
        try:
            pipeline_input = PipelineInput(
                name=self.state.name,
                parameters=[ParameterInput(name=param.name, value=param.value, type=param.type.name)
                            for param in self.state.parameters] if self.state.parameters else [],
                data_catalog=[
                    DataSetInput(
                        name=ds.name, config=ds.config,
                        tags=[TagInput(key=tag.key, value=tag.value) for tag in ds.tags] if ds.tags else [])
                    for ds in self.state.data_catalog] if self.state.data_catalog else [],
                tags=[TagInput(key=tag.key, value=tag.value) for tag in self.state.tags] if self.state.tags else [],
                runner=self.state.status[-1].runner, state=PipelineInputStatus.STAGED
                if type == "staged" else PipelineInputStatus.READY)
            await self.client.create_pipeline(pipeline_input=pipeline_input)

        except Exception as e:
            pn.state.notifications.error(
                f"Error cloning and {'staging' if type == 'staged' else 'running'} pipeline: {str(e)}", duration=10000)
            return

        pn.state.notifications.success(
            f"Pipeline cloned and {'staged' if type == 'staged' else 'executed'} successfully.", duration=10000)



    def __panel__(self):
        return self._content
