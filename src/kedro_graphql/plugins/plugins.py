from abc import ABC, abstractmethod
from kedro_graphql.decorators import gql

class Plugin(ABC):

    @abstractmethod
    def __input__(self, input: str) -> [str]:
        pass

    @abstractmethod 
    def __submit__(self, input: str) -> str:
        pass

@gql(name = "text_in")
class ExampleTextInPlugin(Plugin):
    
    def __input__(self, input: str) -> [str]:
        print("plugin example")
        return [input]

    def __submit__(self, input: str) -> str:
        return input