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
from kedro_graphql.viz.decorators import gql_form
from kedro_graphql.viz.components.template import KedroGraphqlMaterialTemplate

@gql_form(pipeline = "example00")
class Example00PipelineFormV1(pn.viewable.Viewer):
#    client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    config = param.Dict()
    pipeline_name = param.String()
    monitor_pathname = param.String()
    form = param.String()

    def navigate(self, event):
            ## NEEDS WORK 
            pn.state.location.pathname = self.monitor_pathname
            pn.state.location.reload = True
    
    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        pn.bind(self.navigate, run_button, watch=True)
        return pn.Card("An example pipeline form.", 
            pn.Row(
              pn.widgets.TextInput(name='Text Input', placeholder='Enter a string here...'),
            ),
            pn.Row(
                run_button
            ),
            sizing_mode = "stretch_width",
            title='Form')
        
@gql_form(pipeline = "example00")
class Example00PipelineFormV2(pn.viewable.Viewer):
#    client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    config = param.Dict()
    pipeline_name = param.String()
    monitor_pathname = param.String()
    form = param.String()

    def navigate(self, event):
        ## NEEDS WORK 
        pn.state.location.pathname = self.monitor_pathname
        pn.state.location.reload = True
 
    
    def __panel__(self):
        run_button = pn.widgets.Button(name='Run', button_type='success')
        pn.bind(self.navigate, run_button, watch=True)
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
 