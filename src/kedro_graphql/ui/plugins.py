# ui plugin examples

import numpy as np
import pandas as pd
from bokeh.plotting import figure
import tempfile
from tempfile import _TemporaryFileWrapper
import param
import panel as pn
from kedro_graphql.models import Pipeline
from kedro_graphql.ui.decorators import ui_data, ui_form
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import PipelineInput
import json
pn.extension('filedropper')


# pipeline: example00

class BaseExample00Form(pn.viewable.Viewer):
    client = param.ClassSelector(class_=KedroGraphqlClient)
    dashboard = param.String(default="dashboard")
    text_in = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    text_out = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    duration = param.Number(default=3)
    example = param.String(default="hello")

    def navigate(self, pipeline_id: str):
        pn.state.location.search = "?component=" + \
            self.dashboard+"&pipeline=example00&id=" + pipeline_id

    async def upload(self, file_dropper):
        """write a files contens to a temporary file"""
        for k, v in file_dropper.items():
            self.text_in = tempfile.NamedTemporaryFile(delete=False)
            self.text_out = tempfile.NamedTemporaryFile(delete=False)
            with open(self.text_in.name, "w") as f:
                f.write(v)
            print(f"Uploaded {k} to {self.text_in.name}")

    @param.depends("text_in", "text_out", 'duration', 'example')
    async def pipeline_input(self):

        input_dict = {"type": "text.TextDataset", "filepath": self.text_in.name}
        output_dict = {"type": "text.TextDataset",
                       "filepath": self.text_out.name}

        # PipelineInput object
        return PipelineInput(**{
            "name": "example00",
            "state": "READY",
            "data_catalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                             {"name": "text_out", "config": json.dumps(output_dict)}],
            "parameters": [{"name": "example", "value": self.example},
                           {"name": "duration", "value": str(self.duration), "type": "FLOAT"}],
            "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
        })

    async def run(self, event):
        p_input = await self.pipeline_input()
        result = await self.client.create_pipeline(p_input)
        self.navigate(result.id)

    def __panel__(self):
        raise NotImplementedError


@ui_form(pipeline="example00")
class Example00PipelineFormV1(BaseExample00Form):

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.upload, file_dropper, watch=True)
        pn.bind(self.run, run_button, watch=True)

        form = pn.Card(
            "An example pipeline form.",
            pn.Row(
                file_dropper
            ),
            pn.Row(
                run_button
            ),
            sizing_mode="stretch_width",
            title='Form')

        return form


@ui_form(pipeline="example00")
class Example00PipelineFormV2(BaseExample00Form):

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.upload, file_dropper, watch=True)
        pn.bind(self.run, run_button, watch=True)
        form = pn.Card(
            "Another example pipeline form.",
            pn.Row(
                pn.widgets.TextInput.from_param(
                    self.param.example, name='example', placeholder='Enter a string here...'),
            ),
            pn.Row(
                pn.widgets.NumberInput.from_param(
                    self.param.duration, name='duration', placeholder='Enter a number here...')
            ),
            pn.Row(
                file_dropper
            ),
            pn.Row(
                run_button
            ),
            sizing_mode="stretch_width",
            title='Form')

        return form


@ui_data(pipeline="example00")
class Example00Data00(pn.viewable.Viewer):
    client = param.ClassSelector(class_=KedroGraphqlClient)
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default="Table 1")

    def __panel__(self):

        # Create a sample DataFrame
        data = {
            'col1': np.random.randint(0, 10, 5),
            'col2': np.random.rand(5),
            'col3': ['A', 'B', 'A', 'C', 'B']
        }

        df = pd.DataFrame(data)

        df_widget = pn.widgets.Tabulator(df,
                                         theme='materialize',
                                         show_index=False)
        return pn.Card(df_widget)


@ui_data(pipeline="example00")
class Example00Data01(pn.viewable.Viewer):
    client = param.ClassSelector(class_=KedroGraphqlClient)
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default="Plot 1")

    def __panel__(self):

        p1 = figure(height=250, sizing_mode='stretch_width', margin=5)
        p2 = figure(height=250, sizing_mode='stretch_width', margin=5)

        p1.line([1, 2, 3], [1, 2, 3])
        p2.circle([1, 2, 3], [1, 2, 3])

        c1 = pn.Card(p1, pn.layout.Divider(), p2,
                     title="An example pipeline dashboard", sizing_mode='stretch_width')
        return c1


# pipeline: example01
class BaseExample01Form(pn.viewable.Viewer):
    client = param.ClassSelector(class_=KedroGraphqlClient)
    dashboard = param.String(default="dashboard")
    text_in = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    uppercase = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    reversed = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    timestamped = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)

    duration = param.Number(default=3)
    example = param.String(default="hello")

    def navigate(self, pipeline_id: str):
        pn.state.location.search = "?component=" + \
            self.dashboard+"&pipeline=example00&id=" + pipeline_id

    async def upload(self, file_dropper):
        """write a files contens to a temporary file"""
        for k, v in file_dropper.items():
            self.text_in = tempfile.NamedTemporaryFile(delete=False)
            self.uppercase = tempfile.NamedTemporaryFile(delete=False)
            self.reversed = tempfile.NamedTemporaryFile(delete=False)
            self.timestamped = tempfile.NamedTemporaryFile(delete=False)
            with open(self.text_in.name, "w") as f:
                f.write(v)
            print(f"Uploaded {k} to {self.text_in.name}")

    @param.depends("text_in", "uppercase", 'reversed', 'timestamped')
    async def pipeline_input(self):

        text_in_dict = {"type": "text.TextDataset", "filepath": self.text_in.name}
        uppercase_dict = {"type": "text.TextDataset",
                          "filepath": self.uppercase.name}
        reversed_dict = {"type": "text.TextDataset",
                         "filepath": self.reversed.name}
        timestamped_dict = {"type": "text.TextDataset",
                            "filepath": self.timestamped.name}

        # PipelineInput object
        return PipelineInput(**{
            "name": "example01",
            "state": "READY",
            "data_catalog": [{"name": "text_in", "config": json.dumps(text_in_dict)},
                             {"name": "uppercase",
                                 "config": json.dumps(uppercase_dict)},
                             {"name": "reversed", "config": json.dumps(reversed_dict)},
                             {"name": "timestamped", "config": json.dumps(timestamped_dict)}],
            "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
        })

    async def run(self, event):
        p_input = await self.pipeline_input()
        result = await self.client.create_pipeline(p_input)
        self.navigate(result.id)

    def __panel__(self):
        raise NotImplementedError


@ui_form(pipeline="example01")
class Example01PipelineFormV1(BaseExample01Form):

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.upload, file_dropper, watch=True)
        pn.bind(self.run, run_button, watch=True)

        form = pn.Card(
            "An example pipeline form.",
            pn.Row(
                file_dropper
            ),
            pn.Row(
                run_button
            ),
            sizing_mode="stretch_width",
            title='Form')

        return form
