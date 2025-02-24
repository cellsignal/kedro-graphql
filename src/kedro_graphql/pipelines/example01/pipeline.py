"""
This is a boilerplate pipeline 'example01'
generated using Kedro 0.19.11
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import append_timestamp, reverse, uppercase


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(uppercase, inputs="text_in", outputs="uppercased", name="uppercase_node"),
        node(reverse, inputs="uppercased", outputs="reversed", name="reverse_node"),
        node(append_timestamp, inputs="reversed", outputs="timestamped", name="timestamp_node"),
    ])
