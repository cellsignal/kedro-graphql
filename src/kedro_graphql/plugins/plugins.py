import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import strawberry

from kedro_graphql.decorators import (
    gql_mutation,
    gql_query,
    gql_resolver,
    gql_subscription,
)
from kedro_graphql.models import DataSetInput, ParameterInput


class IOResolverPlugin(ABC):
    """
    Implement this class to define custom behavior for pipeline inputs and
    outputs.  The methods of the class will called prior to pipeline 
    execution.
    """
    @abstractmethod
    def __input__(self, input: ParameterInput | DataSetInput) -> [ParameterInput | DataSetInput]:
        pass

    @abstractmethod
    def __submit__(self, input: ParameterInput | DataSetInput) -> ParameterInput | DataSetInput:
        pass


@gql_resolver(name="text_in")
class ExampleTextInPlugin(IOResolverPlugin):

    def __input__(self, input: ParameterInput | DataSetInput) -> [ParameterInput | DataSetInput]:
        print("plugin example", input)
        return [input]

    def __submit__(self, input: ParameterInput | DataSetInput) -> ParameterInput | DataSetInput:
        return input


@gql_query()
@strawberry.type
class ExampleQueryTypePlugin():
    @strawberry.field
    def hello_world(self) -> str:
        return "Hello World"


@gql_mutation()
@strawberry.type
class ExampleMutationTypePlugin():
    @strawberry.mutation
    def hello_world(self, message: str = "World") -> str:
        return "Hello " + message


@gql_subscription()
@strawberry.type
class ExampleSubscriptionTypePlugin():
    @strawberry.subscription
    async def hello_world(self, message: str = "World", target: int = 11) -> AsyncGenerator[str, None]:
        for i in range(target):
            yield str(i) + " Hello " + message
            await asyncio.sleep(0.5)


## viz plugin examples

import param
import panel as pn
from kedro_graphql.models import Pipeline
from kedro_graphql.ui.decorators import viz_data, viz_form
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import PipelineInput
import json
pn.extension('filedropper')
import tempfile


@viz_form(pipeline = "example00")
class Example00PipelineFormV1(pn.viewable.Viewer):
    client = KedroGraphqlClient()
    pathname_dashboard = param.String()
    tmpf_in = None
    tmpf_out = None


    def upload(self, file_dropper):
        """write a files contens to a temporary file"""
        print("UPLOAD")
        for k, v in file_dropper.items():
            self.tmpf_in = tempfile.NamedTemporaryFile(delete=False)
            self.tmpf_out = tempfile.NamedTemporaryFile(delete=False)
            print(self.tmpf_in)
            print(self.tmpf_in.name)

            with open(self.tmpf_in.name, "w") as f:
                f.write(v)

    async def run(self, run_button):

        input_dict = {"type": "text.TextDataset", "filepath": self.tmpf_in.name}
        output_dict = {"type": "text.TextDataset", "filepath": self.tmpf_out.name}
        
        ## PipelineInput object
        p = PipelineInput(**{
                          "name": "example00",
                          "state": "READY",
                          "data_catalog":[{"name": "text_in", "config": json.dumps(input_dict)},
                                          {"name": "text_out", "config": json.dumps(output_dict)}],
                          "parameters": [{"name":"example", "value":"hello"},
                                         {"name": "duration", "value": "3", "type": "FLOAT"}],
                          "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                         })
        
        
        
        result = await self.client.createPipeline(p)
        self.navigate(result.id)

    def navigate(self, pipeline_id: str):
        pn.state.location.pathname = self.pathname_dashboard
        pn.state.location.search = "?pipeline=example00&id="+ pipeline_id
        pn.state.location.reload = True
    
    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        file_dropper = pn.widgets.FileDropper(multiple=False)
        pn.bind(self.run, run_button, watch=True)
        pn.bind(self.upload, file_dropper, watch=True)

        form = pn.Card("An example pipeline form.", 
               pn.Row(
                   file_dropper
               ),
               pn.Row(
                   run_button
               ),
               sizing_mode = "stretch_width",
               title='Form')

        return form

        
@viz_form(pipeline = "example00")
class Example00PipelineFormV2(pn.viewable.Viewer):
    client = KedroGraphqlClient()
    pathname_dashboard = param.String()

    def navigate(self, pipeline_id):
        pn.state.location.pathname = self.pathname_dashboard
        pn.state.location.search = "?pipeline=example00&id="+ pipeline_id
        pn.state.location.reload = True

    async def run(self, event):
        
        input_dict = {"type": "text.TextDataset", "filepath": "./data/01_raw/text_in.txt"}
        output_dict = {"type": "text.TextDataset", "filepath": "./data/02_intermediate/text_out.txt"}

        p = PipelineInput(**{
                          "name": "example00",
                          "state": "READY",
                          "data_catalog":[{"name": "text_in", "config": json.dumps(input_dict)},
                                          {"name": "text_out", "config": json.dumps(output_dict)}],
                          "parameters": [{"name":"example", "value":"hello"},
                                         {"name": "duration", "value": "3", "type": "FLOAT"}],
                          "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                         })
        
        
        
        result = await self.client.createPipeline(p)
        self.navigate(result.id)

    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        pn.bind(self.run, run_button, watch=True)
        form = pn.Card("Another example pipeline form.", 
            pn.Row(
              pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
            ),
            pn.Row(
              pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
            ),
            pn.Row(
              pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
            ),
            pn.Row(
                run_button
            ),
            sizing_mode = "stretch_width",
            title='Form')

        return form
 
 

from bokeh.plotting import figure
import datetime as dt
import pandas as pd

@viz_data(pipeline = "example00")
class Example00Data00(pn.viewable.Viewer):
    id = param.String(default = "")
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default = "Table 1")

    def __panel__(self):

        df = pd.DataFrame({
            'name': ["example00"],
            'id': ["0000000000001"],
            'status': ['RUNNING'],
            'created': [dt.date(2019, 1, 1)],
            'tag:submitted by': ["username"],
        }, index=[0])
        
        
        df_widget = pn.widgets.Tabulator(df, 
                                         theme='materialize',
                                         show_index=False)
        return pn.Card(df_widget, self.pipeline)


@viz_data(pipeline = "example00")
class Example00Data01(pn.viewable.Viewer):
    id = param.String(default = "")
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default = "Plot 1")

    def __panel__(self):

        p1 = figure(height=250, sizing_mode='stretch_width', margin=5)
        p2 = figure(height=250, sizing_mode='stretch_width', margin=5)
        
        p1.line([1, 2, 3], [1, 2, 3])
        p2.circle([1, 2, 3], [1, 2, 3])
        
        c1 = pn.Card(p1, pn.layout.Divider(), p2, title="An example pipeline dashboard", sizing_mode='stretch_width')
        return c1


@viz_data(pipeline = "example00")
class Example00Data01(pn.viewable.Viewer):
    id = param.String(default = "")
    pipeline = param.ClassSelector(class_=Pipeline)
    title = param.String(default = "Plot 2")

    def __panel__(self):


        p3 = figure(height=250, sizing_mode='stretch_width', margin=5)
        p4 = figure(height=250, sizing_mode='stretch_width', margin=5)
        
        p3.line([1, 2, 3], [1, 2, 3])
        p4.circle([1, 2, 3], [1, 2, 3])
        
        c2 = pn.Card(p3, pn.layout.Divider(), p4, title="Another example pipeline dashboard", sizing_mode='stretch_width')
        return c2