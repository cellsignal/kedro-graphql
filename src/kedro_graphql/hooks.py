from typing import Any

from kedro.framework.hooks import hook_impl
from kedro.io import CatalogProtocol
from kedro.pipeline import Pipeline


class InvalidPipeline(Exception):
    """Custom exception for invalid pipeline."""

    def __init__(self, message="The pipeline is invalid"):
        self.message = message
        super().__init__(self.message)


class DataValidationHooks:
    """
    A Kedro hook class to validate the existence of input datasets before running a pipeline.
    """

    @hook_impl
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol
    ) -> None:
        """Hook to be invoked before a pipeline runs.

        Args:
            run_params: The params used to run the pipeline.
            pipeline: The ``Pipeline`` that will be run.
            catalog: An implemented instance of ``CatalogProtocol`` to be used during the run.
        """

        # Only check the free inputs (excluding parameters) for validation
        filtered_keys = [key for key in pipeline.inputs() if not key.startswith('params:') and key != 'parameters']

        # Check to see if all free inputs exist
        for input in filtered_keys:
            if not catalog.exists(input):
                raise InvalidPipeline(f"Input dataset {input} does not exist.")
