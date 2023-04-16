from abc import ABC, abstractmethod
from kedro_graphql.decorators import gql
from kedro_graphql.models import ParameterInput, DataSetInput

class ResolverPlugin(ABC):
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
class ExampleTextInPlugin(ResolverPlugin):
    
    def __input__(self, input: ParameterInput | DataSetInput) -> [ParameterInput | DataSetInput]:
        print("plugin example", input)
        return [input]

    def __submit__(self, input: ParameterInput | DataSetInput) -> ParameterInput | DataSetInput:
        return input