"""
This is a boilerplate pipeline 'event00'
generated using Kedro 0.19.11
"""
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import PipelineInput
from cloudevents.pydantic.v1 import CloudEvent
from cloudevents.conversion import from_json
import json
import asyncio
import tempfile
from omegaconf.dictconfig import DictConfig
from omegaconf import OmegaConf


def create_pipeline_input(id: str, event: CloudEvent) -> PipelineInput:
    """
    Create a PipelineInput object based on the provided ID and CloudEvent.

    Args:
        id (str): The ID of the pipeline to which this node belongs.
        event (CloudEvent): A CloudEvent object containing event data.

    Returns:
        PipelineInput: A PipelineInput object ready for use in the pipeline.
    """

    tmp = tempfile.gettempdir()
    mock_text_in = tmp + "/text_in.txt"
    mock_text_out = tmp + "/text_out.txt"

    with open(mock_text_in, "w") as f:
        f.write("Hello, world!")

    with open(mock_text_out, "w") as f:
        f.write("Goodbye, world!")

    input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
    output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}
    return PipelineInput(**{
        "parent": id,
        "name": "example00",
        "state": "STAGED",
        "data_catalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                         {"name": "text_out", "config": json.dumps(output_dict)}],
        "parameters": [{"name": "example", "value": "hello"},
                       {"name": "duration", "value": "0", "type": "FLOAT"}],
        "tags": [{"key": "author", "value": "opensean"},
                 {"key": "package", "value": "kedro-graphql"}]
    })


# i dont know why kedro serializes the event as a DictConfig, it should be string
# need to look into the details of the MemoryDataset and parameters handling
def run_example00_via_api(id: str, event: DictConfig) -> dict:
    """
    Example node that parse a cloudevent passed as json
    and triggers the example00 pipeline via the GraphQL API.

    Args:
        id (str): The ID of the pipeline to which this node belongs.
        event (str): A JSON string representing a CloudEvent.

    Returns:
        dict: A dictionary representation of the created pipeline.
    """
    event = from_json(CloudEvent, json.dumps(OmegaConf.to_container(event)))

    client = KedroGraphqlClient(uri_graphql="http://localhost:5000/graphql",
                                uri_ws="ws://localhost:5000/graphql")

    pipeline_input = create_pipeline_input(id, event)

    pipeline = asyncio.run(client.create_pipeline(pipeline_input))

    asyncio.run(client.close_sessions())
    return pipeline.encode(encoder="dict")
