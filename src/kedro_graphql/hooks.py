import os
from typing import Any

from kedro.framework.hooks import hook_impl
from kedro.io import CatalogProtocol
from kedro.pipeline import Pipeline
from kedro_graphql.logs.logger import logger

from .config import load_config

CONFIG = load_config()

logger.debug("configuration loaded by {s}".format(s=__name__))


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
        filtered_keys = [key for key in pipeline.inputs(
        ) if not key.startswith('params:') and key != 'parameters']

        # Check to see if all free inputs exist
        for input in filtered_keys:
            if not catalog.exists(input):
                raise InvalidPipeline(f"Input dataset {input} does not exist.")


class DataLoggingHooks:
    """
    A Kedro hook class to save pipeline logs to S3 bucket. 
    """

    def save_meta(self, run_params: dict[str, Any], catalog: CatalogProtocol):
        d = catalog.load("gql_meta")
        d["run_params"] = run_params
        catalog.save("gql_meta", d)

    def save_logs(self, catalog: CatalogProtocol, session_id: str, celery_task_id: str):
        log_dir = os.path.join(CONFIG["KEDRO_GRAPHQL_LOG_TMP_DIR"], celery_task_id)
        log_files = ["info.log", "errors.log"]

        for log_file in log_files:
            log_path = os.path.join(log_dir, log_file)
            if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
                with open(log_path, "r") as file:
                    logs = file.read()
                d = catalog._get_dataset("gql_logs")
                d.save({f"logs/{session_id}/{log_file}": logs})

    @hook_impl
    def before_pipeline_run(self, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol):
        # Clear previous logs before pipeline run
        log_dir = os.path.join(
            CONFIG["KEDRO_GRAPHQL_LOG_TMP_DIR"], run_params["celery_task_id"])
        log_files = ["info.log", "errors.log"]

        for log_file in log_files:
            log_path = os.path.join(log_dir, log_file)
            if os.path.exists(log_path):
                open(log_path, 'w').close()

        if CONFIG.get('KEDRO_GRAPHQL_LOG_PATH_PREFIX'):
            self.save_meta(run_params, catalog)

    @hook_impl
    def after_pipeline_run(
            self, run_params: dict[str, Any],
            run_result: dict[str, Any],
            pipeline: Pipeline, catalog: CatalogProtocol):
        if CONFIG.get('KEDRO_GRAPHQL_LOG_PATH_PREFIX'):
            self.save_logs(
                catalog, run_params["session_id"], run_params["celery_task_id"])

    @hook_impl
    def on_pipeline_error(self, error: Exception, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol):
        if CONFIG.get('KEDRO_GRAPHQL_LOG_PATH_PREFIX'):
            self.save_logs(
                catalog, run_params["session_id"], run_params["celery_task_id"])


validation_hooks = DataValidationHooks()
logging_hooks = DataLoggingHooks()
