# ui plugin examples

import plotly.graph_objects as go
import numpy as np
import pandas as pd
from bokeh.plotting import figure
import tempfile
from tempfile import _TemporaryFileWrapper
import param
import panel as pn
from kedro_graphql.models import Pipeline
from kedro_graphql.ui.decorators import ui_data, ui_form, ui_dashboard
from kedro_graphql.ui.components.pipeline_monitor import PipelineMonitor
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import PipelineInput
import json

pn.extension('filedropper')


# pipeline: example00

class BaseExample00Form(pn.viewable.Viewer):
    """Base class for example00 pipeline forms.
    This class provides the basic functionality for uploading files, running the pipeline,
    and navigating to the pipeline dashboard.

    Attributes:
        spec (dict): The specification for the UI, including configuration and pages.
        text_in (_TemporaryFileWrapper): A temporary file wrapper for the input text file.
        text_out (_TemporaryFileWrapper): A temporary file wrapper for the output text file.
        duration (int): The duration parameter for the pipeline.
        example (str): An example string parameter for the pipeline.
        button_disabled (bool): A flag to disable the run button until a file is uploaded.

    Methods:
        navigate(pipeline_id: str): Navigate to the pipeline dashboard with the given ID.
        upload(file_dropper): Write the contents of the uploaded file to a temporary file.
        pipeline_input(): Create a PipelineInput object with the current parameters.
        run(event): Run the pipeline with the current input and parameters.
        __panel__(): Return a Panel component for the form.

    This class should be subclassed to implement specific forms for the example00 pipeline.
    """
    spec = param.Dict(default={})
    text_in = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    text_out = param.ClassSelector(
        class_=_TemporaryFileWrapper, default=None)
    duration = param.Number(default=3)
    example = param.String(default="hello")
    disabled = param.Boolean(default=True)

    def navigate(self, pipeline_id: str):
        """Navigate to the pipeline dashboard with the given ID."""
        pn.state.location.search = "?page=dashboard&pipeline=example00&id=" + pipeline_id

    async def upload(self, file_dropper):
        """write a files contents to a temporary file"""
        for k, v in file_dropper.items():
            self.text_in = tempfile.NamedTemporaryFile(delete=False)
            self.text_out = tempfile.NamedTemporaryFile(delete=False)
            with open(self.text_in.name, "w") as f:
                f.write(v)
            print(f"Uploaded {k} to {self.text_in.name}")
            self.disabled = False

    @param.depends("text_in", "text_out", 'duration', 'example')
    async def pipeline_input(self):
        """Create a PipelineInput object with the current parameters."""

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

    @param.depends('disabled')
    async def build_run_button(self):
        button = pn.widgets.Button(
            name='Run', button_type='success', disabled=self.disabled)
        pn.bind(self.run, button, watch=True)
        yield button

    async def run(self, event):
        """Run the pipeline with the current input and parameters."""
        p_input = await self.pipeline_input()
        result = await self.spec["config"]["client"].create_pipeline(p_input)
        self.navigate(result.id)

    def __panel__(self):
        raise NotImplementedError


@ui_form(pipeline="example00")
class Example00PipelineFormV1(BaseExample00Form):
    """Form for the example00 pipeline.
    This form allows users to upload a file, run the pipeline, and navigate to the pipeline dashboard.
    It inherits from BaseExample00Form and implements the __panel__ method to create the form layout.
    """

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        """Create the Panel component for the example00 pipeline form."""
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.upload, file_dropper, watch=True)

        form = pn.Card(
            "An example pipeline form.",
            pn.Row(
                file_dropper
            ),
            pn.Row(
                self.build_run_button
            ),
            sizing_mode="stretch_width",
            title='Form')

        return form


@ui_form(pipeline="example00")
class Example00PipelineFormV2(BaseExample00Form):
    """Another example form for the example00 pipeline.
    This form allows users to enter additional parameters and upload a file.
    It inherits from BaseExample00Form and implements the __panel__ method to create the form layout.
    """

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        """Create the Panel component for the example00 pipeline form with additional parameters."""
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.upload, file_dropper, watch=True)

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
                self.build_run_button
            ),
            sizing_mode="stretch_width",
            title='Form')

        return form


@ui_data(pipeline="example00")
class Example00Data00(pn.viewable.Viewer):
    """Data viewer for the example00 pipeline.
    This viewer displays a sample DataFrame in a Tabulator widget.
    It inherits from pn.viewable.Viewer and implements the __panel__ method to create the data view.

    Attributes:
        spec (dict): The specification for the UI, including configuration and pages.
        id (str): The ID of the data viewer.
        pipeline (Pipeline): The Kedro pipeline associated with this data viewer.
        title (str): The title of the data viewer.
    """
    spec = param.Dict(default={})
    id = param.String(default="")
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default="Plot 1")

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
    """Another data viewer for the example00 pipeline.
    This viewer displays a sample plot using Bokeh figures.
    It inherits from pn.viewable.Viewer and implements the __panel__ method to create the plot view.

    Attributes:
        spec (dict): The specification for the UI, including configuration and pages.
        id (str): The ID of the data viewer.
        pipeline (Pipeline): The Kedro pipeline associated with this data viewer.
        title (str): The title of the data viewer.
    """
    spec = param.Dict(default={})
    id = param.String(default="")
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default="Plot 1")

    def __panel__(self):

        p1 = figure(height=250, sizing_mode='stretch_width', margin=5)
        p2 = figure(height=250, sizing_mode='stretch_width', margin=5)

        p1.line([1, 2, 3], [1, 2, 3])
        p2.circle([1, 2, 3], [1, 2, 3], radius=0.1,
                  fill_color="orange", line_color="black")

        c1 = pn.Card(p1, pn.layout.Divider(), p2,
                     title="An example pipeline dashboard", sizing_mode='stretch_width')
        return c1


# pipeline: example01
class BaseExample01Form(pn.viewable.Viewer):
    """Base class for example01 pipeline forms.
    This class provides the basic functionality for uploading files, running the pipeline,
    and navigating to the pipeline dashboard.

    Attributes:
        spec (dict): The specification for the UI, including configuration and pages.
        text_in (_TemporaryFileWrapper): A temporary file wrapper for the input text file.
        uppercase (_TemporaryFileWrapper): A temporary file wrapper for the uppercase output file.
        reversed (_TemporaryFileWrapper): A temporary file wrapper for the reversed output file.
        timestamped (_TemporaryFileWrapper): A temporary file wrapper for the timestamped output file.
        duration (int): The duration parameter for the pipeline.
        example (str): An example string parameter for the pipeline.

    Methods:
        navigate(pipeline_id: str): Navigate to the pipeline dashboard with the given ID.
        upload(file_dropper): Write the contents of the uploaded file to temporary files.
        pipeline_input(): Create a PipelineInput object with the current parameters.
        run(event): Run the pipeline with the current input and parameters.
        __panel__(): Return a Panel component for the form.

    This class should be subclassed to implement specific forms for the example01 pipeline.
    """

    spec = param.Dict(default={})
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
    disabled = param.Boolean(default=True)

    def navigate(self, pipeline_id: str):
        """Navigate to the pipeline dashboard with the given ID."""
        pn.state.location.search = "?page=dashboard&pipeline=example00&id=" + pipeline_id

    async def upload(self, file_dropper):
        """write a files contents to a temporary file"""
        for k, v in file_dropper.items():
            self.text_in = tempfile.NamedTemporaryFile(delete=False)
            self.uppercase = tempfile.NamedTemporaryFile(delete=False)
            self.reversed = tempfile.NamedTemporaryFile(delete=False)
            self.timestamped = tempfile.NamedTemporaryFile(delete=False)
            with open(self.text_in.name, "w") as f:
                f.write(v)
            print(f"Uploaded {k} to {self.text_in.name}")
            self.disabled = False

    @param.depends("text_in", "uppercase", 'reversed', 'timestamped')
    async def pipeline_input(self):
        """Create a PipelineInput object with the current parameters."""

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
                             {"name": "uppercased",
                                 "config": json.dumps(uppercase_dict)},
                             {"name": "reversed", "config": json.dumps(reversed_dict)},
                             {"name": "timestamped", "config": json.dumps(timestamped_dict)}],
            "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
        })

    @param.depends('disabled')
    async def build_run_button(self):
        button = pn.widgets.Button(
            name='Run', button_type='success', disabled=self.disabled)
        pn.bind(self.run, button, watch=True)
        yield button

    async def run(self, event):
        """Run the pipeline with the current input and parameters."""
        p_input = await self.pipeline_input()
        result = await self.spec["config"]["client"].create_pipeline(p_input)
        self.navigate(result.id)

    def __panel__(self):
        raise NotImplementedError


@ui_form(pipeline="example01")
class Example01PipelineFormV1(BaseExample01Form):
    """Form for the example01 pipeline.
    This form allows users to upload a file, run the pipeline, and navigate to the pipeline dashboard.
    It inherits from BaseExample01Form and implements the __panel__ method to create the form layout.
    """

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.upload, file_dropper, watch=True)

        form = pn.Card(
            "An example pipeline form.",
            pn.Row(
                file_dropper
            ),
            pn.Row(
                self.build_run_button
            ),
            sizing_mode="stretch_width",
            title='Form')

        return form


pn.extension('plotly')


@ui_dashboard(pipeline="example01")
class Example01PipelineUIV1(pn.viewable.Viewer):
    """Dashboard for the example01 pipeline.
    This dashboard displays the pipeline stages and allows users to monitor the pipeline's progress.
    It inherits from pn.viewable.Viewer and implements the __panel__ method to create the dashboard layout.
    Attributes:
        spec (dict): The specification for the UI, including configuration and pages.
        id (str): The ID of the pipeline.
        pipeline (Pipeline): The Kedro pipeline associated with this dashboard.
    """

    spec = param.Dict(default={})
    id = param.String(default="")
    pipeline = param.ClassSelector(class_=Pipeline)

    def __init__(self, **params):
        super().__init__(**params)

    def draw_pipeline(self):
        nodes = ["stage 1", "stage 2", "stage 3"]
        # it would be nice to get nodes from the pipeline object instead

        # Define node colors, default color is blue
        node_colors = ['blue'] * len(nodes)
        node_colors[1] = 'green'  # Change color of the second node to green

        # Define edges as tuples of node indices
        node_trace = go.Scatter(
            x=nodes,
            y=[0, 0, 0],
            mode='lines+markers',
            text=[nodes],
            marker=dict(
                size=20,
                color=node_colors
            ),
            line=dict(width=2, color='gray'),
            textposition='bottom center'
        )
        fig = go.Figure(data=[node_trace],
                        layout=go.Layout(showlegend=False))

        fig.update_layout({
            "plot_bgcolor": "rgba(0, 0, 0, 0)",
            "paper_bgcolor": "rgba(0, 0, 0, 0)",
            'xaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': True},
            'yaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': False},
            'hovermode': False,
            'height': 100,
            'margin': dict(t=0, b=0, l=0, r=0),
        })
        return pn.pane.Plotly(fig, config={'displayModeBar': False, 'scrollZoom': False})

    @param.depends("spec", "pipeline")
    async def build_ui(self):
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        monitor = PipelineMonitor(
            client=self.spec["config"]["client"], pipeline=self.pipeline)
        ui = pn.Column(
            pn.Row(self.draw_pipeline()),
            pn.Row(monitor),
            sizing_mode="stretch_width")

        yield ui

    def __panel__(self):

        pn.state.location.sync(self, {"id": "id"})
        return self.build_ui
