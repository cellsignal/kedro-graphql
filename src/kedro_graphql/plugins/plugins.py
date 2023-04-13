from abc import ABC, abstractmethod
from kedro_graphql.decorators import gql

class PluginResolver(ABC):

    @abstractmethod
    def __input__(self, input: str) -> [str]:
        pass

    @abstractmethod 
    def __submit__(self, input: str) -> str:
        pass

@gql(name = "text_in")
class ExampleTextInPlugin(PluginResolver):
    
    def __input__(self, input: str) -> [str]:
        print("plugin example", input)
        return [input]

    def __submit__(self, input: str) -> str:
        return input