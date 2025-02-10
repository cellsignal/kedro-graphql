"""
This is a boilerplate pipeline 'example01'
generated using Kedro 0.19.11
"""

from kedro.pipeline import Pipeline, node, pipeline
from .nodes import uppercase, reverse, append_timestamp

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(uppercase, inputs="text_in", outputs="uppercase_out", name="uppercase_node"),
        node(reverse, inputs="uppercase_out", outputs="reversed_out", name="reverse_node"),
        node(append_timestamp, inputs="reversed_out", outputs="timestamp_out", name="timestamp_node"),
    ])
