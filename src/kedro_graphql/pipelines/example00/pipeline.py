"""
This is a boilerplate pipeline 'example00'
generated using Kedro 0.18.4
"""

from kedro.pipeline import Pipeline, node, pipeline
from .nodes import echo

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=echo,
            inputs=["text_in", "params:example", "parameters"],
            outputs="text_out",
            name="echo_node"
        )
    ])
