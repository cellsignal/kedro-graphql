from abc import ABC, abstractmethod
from kedro_graphql.decorators import gql, gql_type
from kedro_graphql.models import ParameterInput, DataSetInput
import strawberry

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

@gql(name = "text_in")
class ExampleTextInPlugin(IOResolverPlugin):
    
    def __input__(self, input: ParameterInput | DataSetInput) -> [ParameterInput | DataSetInput]:
        print("plugin example", input)
        return [input]

    def __submit__(self, input: ParameterInput | DataSetInput) -> ParameterInput | DataSetInput:
        return input

@gql_type(type = "query")
@strawberry.type
class ExampleTypePlugin():
    @strawberry.field
    def helloWorld(self) -> str:
        return "Hello World"