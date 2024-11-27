from abc import ABC, abstractmethod
import asyncio
from kedro_graphql.decorators import gql_resolver, gql_query, gql_mutation, gql_subscription
from kedro_graphql.models import ParameterInput, DataSetInput
import strawberry
from typing import AsyncGenerator

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

@gql_resolver(name = "text_in")
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


## viz plugin example

## some code commented out because it has not been implemented
import param
#from kedro_graphql.client import KedroGraphqlClient
import panel as pn
from kedro_graphql.models import Pipeline
from kedro_graphql.config import config
from kedro_graphql.viz.decorators import viz_data, viz_form
from kedro_graphql.viz.client import KedroGraphqlClient
from kedro_graphql.models import PipelineInput
import json

@viz_form(pipeline = "example00")
class Example00PipelineFormV1(pn.viewable.Viewer):
    name = param.String()
    form = param.String()
    monitor_pathname = "/pipelines/monitor"
    client = KedroGraphqlClient()

    async def run(self, event):

        input_dict = {"type": "text.TextDataset", "filepath": "./data/01_raw/text_in.txt"}
        output_dict = {"type": "text.TextDataset", "filepath": "./data/02_intermediate/text_out.txt"}
        
        ## PipelineInput object
        p = PipelineInput(**{
                          "name": "example00",
                          "data_catalog":[{"name": "text_in", "config": json.dumps(input_dict)},
                                          {"name": "text_out", "config": json.dumps(output_dict)}],
                          "parameters": [{"name":"example", "value":"hello"},
                                         {"name": "duration", "value": "3", "type": "FLOAT"}],
                          "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                         })
        
        
        
        result = await self.client.createPipeline(p)
        self.navigate(result.id)

    def navigate(self, pipeline_id: str):
        pn.state.location.pathname = self.monitor_pathname
        pn.state.location.search = "?pipeline="+self.name+"&id="+ pipeline_id
        pn.state.location.reload = True
    
    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        pn.bind(self.run, run_button, watch=True)
        return pn.Card("An example pipeline form.", 
            pn.Row(
              pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
            ),
            pn.Row(
                run_button
            ),
            sizing_mode = "stretch_width",
            title='Form')
        
@viz_form(pipeline = "example01")
class Example00PipelineFormV2(pn.viewable.Viewer):
    name = param.String()
    form = param.String()
    monitor_pathname = "/pipelines/monitor"
    client = KedroGraphqlClient()

    def navigate(self, pipeline_id):
        pn.state.location.pathname = self.monitor_pathname
        pn.state.location.search = "?pipeline="+self.name+"&id="+ pipeline_id
        pn.state.location.reload = True

    async def run(self, event):
        
        input_dict = {"type": "text.TextDataset", "filepath": "./data/01_raw/text_in.txt"}
        output_dict = {"type": "text.TextDataset", "filepath": "./data/02_intermediate/text_out.txt"}
        
        ## PipelineInput object
        p = PipelineInput(**{
                          "name": "example00",
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
        return pn.Card("Another example pipeline form.", 
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
 

from bokeh.plotting import figure
import datetime as dt
import pandas as pd

@viz_data(pipeline = "example00")
class Example00DataV0(pn.viewable.Viewer):
#    client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    config = param.Dict()
    pipeline_name = param.String()
    pipeline_id = param.String()
    display_name = "Summary"

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
        
        return df_widget
 

@viz_data(pipeline = "example00")
class Example00DataV1(pn.viewable.Viewer):
#    client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    config = param.Dict()
    pipeline_name = param.String()
    pipeline_id = param.String()
    display_name = "Analysis 1"

    def __panel__(self):

        p1 = figure(height=250, sizing_mode='stretch_width', margin=5)
        p2 = figure(height=250, sizing_mode='stretch_width', margin=5)
        
        p1.line([1, 2, 3], [1, 2, 3])
        p2.circle([1, 2, 3], [1, 2, 3])
        
        return pn.Card(p1, pn.layout.Divider(), p2, title="An example pipeline dashboard", sizing_mode='stretch_width')
       
@viz_data(pipeline = "example00")
class Example00DataV2(pn.viewable.Viewer):
#    client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    config = param.Dict()
    pipeline_name = param.String()
    pipeline_id = param.String()
    display_name = "Analysis 2"

    def __panel__(self):

        p1 = figure(height=250, sizing_mode='stretch_width', margin=5)
        p2 = figure(height=250, sizing_mode='stretch_width', margin=5)
        
        p1.line([1, 2, 3], [1, 2, 3])
        p2.circle([1, 2, 3], [1, 2, 3])
        
        return pn.Card(p1, pn.layout.Divider(), p2, title="Another example pipeline dashboard", sizing_mode='stretch_width')
 
