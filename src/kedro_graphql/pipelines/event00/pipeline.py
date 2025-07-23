"""
This is a boilerplate pipeline 'event00'
generated using Kedro 0.19.11
"""

from kedro.pipeline import node, Pipeline, pipeline  # noqa
from .nodes import run_example00_via_api


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(run_example00_via_api,
                 inputs=["params:id", "params:event"], outputs="pipeline")
        ]
    )
