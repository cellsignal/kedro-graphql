import asyncio
import json
import logging
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

from celery import Task, shared_task
from kedro import __version__ as kedro_version
from kedro.framework.project import pipelines
from kedro.framework.session import KedroSession
from kedro.io import AbstractDataset, DataCatalog
from omegaconf import OmegaConf

from kedro_graphql.logs.logger import KedroGraphQLLogHandler
from kedro_graphql.utils import add_param_to_feed_dict
from kedro_graphql.runners import init_runner
from kedro_graphql.models import PipelineInput, ParameterInput, Pipeline

# from .config import load_config
from .models import DataSet, State
from .client import PIPELINE_GQL

from cloudevents.pydantic.v1 import CloudEvent
from cloudevents.conversion import from_json, to_json

logger = logging.getLogger(__name__)
# CONFIG = load_config()
# logger.debug("configuration loaded by {s}".format(s=__name__))


class KedroGraphqlTask(Task):

    _db = None
    _gql_config = None

    @property
    def db(self):
        if self._db is None:
            self._db = self.app.kedro_graphql_backend
        return self._db

    @property
    def gql_config(self):
        if self._gql_config is None:
            self._gql_config = self.app.kedro_graphql_config
        return self._gql_config

    def before_start(self, task_id, args, kwargs):
        """Handler called before the task starts.

        .. versionadded:: 5.2

        Arguments:
            task_id (str): Unique id of the task to execute.
            args (Tuple): Original arguments for the task to execute.
            kwargs (Dict): Original keyword arguments for the task to execute.

        Returns:
            None: The return value of this handler is ignored.
        """
        handler = KedroGraphQLLogHandler(
            task_id, broker_url=self._app.conf["broker_url"])
        logging.getLogger("kedro").addHandler(handler)
        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.STARTED
        p.status[-1].task_id = task_id
        p.status[-1].task_args = json.dumps(args)
        p.status[-1].task_kwargs = json.dumps(kwargs)
        self.db.update(p)

        try:
            # Create info and error handlers for the run
            # os.makedirs(os.path.join(
            # CONFIG["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id), exist_ok=True)
            os.makedirs(os.path.join(
                self.gql_config["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id), exist_ok=True)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            # info_handler = logging.FileHandler(os.path.join(
            # CONFIG["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id + '/info.log'), 'a')
            info_handler = logging.FileHandler(os.path.join(
                self.gql_config["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id + '/info.log'), 'a')

            info_handler.setLevel(logging.INFO)
            info_handler.setFormatter(formatter)
            # error_handler = logging.FileHandler(os.path.join(
            # CONFIG["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id + '/errors.log'), 'a')
            error_handler = logging.FileHandler(os.path.join(
                self.gql_config["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id + '/errors.log'), 'a')

            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            logging.getLogger("kedro").addHandler(info_handler)
            logging.getLogger("kedro").addHandler(error_handler)
            # logger.info(
            # f"Storing tmp logs in {os.path.join(CONFIG['KEDRO_GRAPHQL_LOG_TMP_DIR'], task_id)}")
            logger.info(
                f"Storing tmp logs in {os.path.join(self.gql_config['KEDRO_GRAPHQL_LOG_TMP_DIR'], task_id)}")

            # Ensure KEDRO_GRAPHQL_LOG_PATH_PREFIX is provided
            # log_path_prefix = CONFIG.get('KEDRO_GRAPHQL_LOG_PATH_PREFIX')
            log_path_prefix = self.gql_config.get('KEDRO_GRAPHQL_LOG_PATH_PREFIX')
            logger.info("Final upload destination for logs:{s}".format(
                s=log_path_prefix))
            if log_path_prefix:

                today = date.today()

                # Add metadata and log datasets to data catalog
                gql_meta = DataSet(name="gql_meta", config=json.dumps({"type": "json.JSONDataset",
                                                                       "filepath": os.path.join(log_path_prefix, f"year={today.year}", f"month={today.month}", f"day={today.day}", str(p.id), "meta.json")}))
                gql_logs = DataSet(name="gql_logs", config=json.dumps({"type": "partitions.PartitionedDataset",
                                                                      "dataset": "text.TextDataset",
                                                                       "path": os.path.join(log_path_prefix, f"year={today.year}", f"month={today.month}", f"day={today.day}", str(p.id))}))
                p.data_catalog.append(gql_meta)
                p.data_catalog.append(gql_logs)

                # Save metadata to S3
                AbstractDataset.from_config(gql_meta.name, json.loads(
                    gql_meta.config)).save(p.serialize())
                p = self.db.update(p)

                logger.info(
                    f"Capturing pipeline metadata in {os.path.join(log_path_prefix,f'year={today.year}',f'month={today.month}',f'day={today.day}',str(p.id),'meta.json')}")
                logger.info(
                    f"Capturing pipeline logs in {os.path.join(log_path_prefix,f'year={today.year}',f'month={today.month}',f'day={today.day}',str(p.id))}")

                # Capture pipeline object returned as an attribute of the task object
                setattr(self, "kedro_graphql_pipeline", p)
            else:
                logger.info(
                    f"Missing KEDRO_GRAPHQL_LOG_PATH_PREFIX in config. Not capturing session logs.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """Success handler.

        Run by the worker if the task executes successfully.

        Arguments:
            retval (Any): The return value of the task.
            task_id (str): Unique id of the executed task.
            args (Tuple): Original arguments for the executed task.
            kwargs (Dict): Original keyword arguments for the executed task.

        Returns:
            None: The return value of this handler is ignored.
        """

        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.SUCCESS
        self.db.update(p)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry handler.

        This is run by the worker when the task is to be retried.

        Arguments:
            exc (Exception): The exception sent to :meth:`retry`.
            task_id (str): Unique id of the retried task.
            args (Tuple): Original arguments for the retried task.
            kwargs (Dict): Original keyword arguments for the retried task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.RETRY
        p.status[-1].task_exception = str(exc)
        p.status[-1].task_einfo = str(einfo)
        self.db.update(p)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Error handler.

        This is run by the worker when the task fails.

        Arguments:
            exc (Exception): The exception raised by the task.
            task_id (str): Unique id of the failed task.
            args (Tuple): Original arguments for the task that failed.
            kwargs (Dict): Original keyword arguments for the task that failed.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.FAILURE
        p.status[-1].task_exception = str(exc)
        p.status[-1].task_einfo = str(einfo)
        self.db.update(p)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Handler called after the task returns.

        Arguments:
            status (str): Current task state.
            retval (Any): Task return value/exception.
            task_id (str): Unique id of the task.
            args (Tuple): Original arguments for the task.
            kwargs (Dict): Original keyword arguments for the task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        finished_at = datetime.now()

        p = self.db.read(id=kwargs["id"])
        p.status[-1].finished_at = finished_at
        p.status[-1].task_result = str(retval)
        self.db.update(p)

        logger.info("Closing log stream")

        # Clean up log handlers
        for handler in logger.handlers:
            if isinstance(handler, KedroGraphQLLogHandler) and handler.topic == task_id:
                handler.flush()
                handler.close()
                handler.broker.connection.delete(task_id)  # delete stream
                handler.broker.connection.close()
            if isinstance(handler, logging.FileHandler):
                handler.close()
        logger.handlers = []

        # Clear logs from temp_logs
        try:
            # Removes the directory and its contents
            # shutil.rmtree(os.path.join(CONFIG["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id))
            shutil.rmtree(os.path.join(
                self.gql_config["KEDRO_GRAPHQL_LOG_TMP_DIR"], task_id))
        except Exception as e:
            # logger.info(
            #    f"Failed to clear logs in {os.path.join(CONFIG['KEDRO_GRAPHQL_LOG_TMP_DIR'].name, task_id)}: {e}")
            logger.info(
                f"Failed to clear logs in {os.path.join(self.gql_config['KEDRO_GRAPHQL_LOG_TMP_DIR'].name, task_id)}: {e}")


@shared_task(bind=True, base=KedroGraphqlTask)
def run_pipeline(self,
                 id: str = None,
                 name: str = None,
                 parameters: dict = None,
                 data_catalog: dict = None,
                 runner: str = None,
                 slices: List[Dict[str, List[str]]] = None,
                 only_missing: bool = False):

    # with KedroSession.create(project_path=Path(__file__).resolve().parent.parent.parent,
    #                         env=CONFIG["KEDRO_GRAPHQL_ENV"],
    #                         conf_source=CONFIG["KEDRO_GRAPHQL_CONF_SOURCE"]) as session:
    with KedroSession.create(project_path=Path(__file__).resolve().parent.parent.parent,
                             env=self.gql_config["KEDRO_GRAPHQL_ENV"],
                             conf_source=self.gql_config["KEDRO_GRAPHQL_CONF_SOURCE"]) as session:

        hook_manager = session._hook_manager

        p = self.db.read(id=id)
        p.status[-1].session = session.session_id
        self.db.update(p)

        # If modified data catalog object with gql_meta and gql_logs datasets exists, use it
        if getattr(self, "kedro_graphql_pipeline", None):
            logger.info("using data_catalog with gql_meta and gql_logs")
            serial = self.kedro_graphql_pipeline.serialize()
            catalog = {**serial["data_catalog"], **data_catalog}
        else:
            logger.info("using data_catalog parameter to build data catalog")
            catalog = data_catalog

        io = DataCatalog.from_config(catalog=catalog)

        # add parameters to DataCatalog using OmegaConf and dotlist notation
        parameters_dotlist = [f"{key}={value}" for key, value in parameters.items()]
        conf_parameters = OmegaConf.to_container(
            OmegaConf.from_dotlist(parameters_dotlist), resolve=True)

        feed_dict = {"parameters": conf_parameters}
        for param_name, param_value in conf_parameters.items():
            add_param_to_feed_dict(feed_dict, param_name, param_value)

        io.add_feed_dict(feed_dict)

        try:
            # Populate the filtering parameters based on the slices input
            tags = None
            from_nodes = None
            to_nodes = None
            node_names = None
            from_inputs = None
            to_outputs = None
            node_namespace = None

            if slices:
                for slice_item in slices:
                    slice_type = slice_item['slice']
                    slice_args = slice_item['args']

                    if slice_type == 'tags':
                        tags = slice_args
                    if slice_type == 'from_nodes':
                        from_nodes = slice_args
                    if slice_type == 'to_nodes':
                        to_nodes = slice_args
                    if slice_type == 'node_names':
                        node_names = slice_args
                    if slice_type == 'from_inputs':
                        from_inputs = slice_args
                    if slice_type == 'to_outputs':
                        to_outputs = slice_args
                    if slice_type == 'node_namespace':
                        node_namespace = slice_args[0]

            record_data = {
                "session_id": session.session_id,
                "celery_task_id": self.request.id,
                "project_path": session._project_path.as_posix(),
                "env": session.load_context().env,
                "kedro_version": kedro_version,
                # Construct the pipeline using only nodes which have this tag attached.
                "tags": tags,
                # A list of node names which should be used as a starting point.
                "from_nodes": from_nodes,
                # A list of node names which should be used as an end point.
                "to_nodes": to_nodes,
                "node_names": node_names,  # Run only nodes with specified names.
                # A list of dataset names which should be used as a starting point.
                "from_inputs": from_inputs,
                # A list of dataset names which should be used as an end point.
                "to_outputs": to_outputs,
                # Specify a particular dataset version (timestamp) for loading
                "load_versions": "",
                # Specify extra parameters that you want to pass to the context initialiser.
                "extra_params": "",
                "pipeline_name": name,
                "namespace": node_namespace,  # Name of the node namespace to run.
                "runner": getattr(runner, "__name__", str(runner)),
            }

            hook_manager.hook.after_catalog_created(
                catalog=io,
                conf_catalog=None,
                conf_creds=None,
                feed_dict=None,
                save_version=None,
                load_versions=None
            )

            hook_manager.hook.before_pipeline_run(
                run_params=record_data,
                pipeline=pipelines.get(name, None),
                catalog=io
            )

            runner = init_runner(runner=runner)

            # Filter the pipeline based on the slices and only_missing parameters
            if only_missing:
                # https://github.com/kedro-org/kedro/blob/06d5a6920cbb6b45c07dca6f77d14bb35e283b19/kedro/runner/runner.py#L154
                free_outputs = pipelines[name].outputs() - set(io.list())
                missing = {ds for ds in io.list() if not io.exists(ds)}
                to_build = free_outputs | missing
                filtered_pipeline = pipelines[name].only_nodes_with_outputs(*to_build) + pipelines[name].from_inputs(
                    *to_build
                )

                # We also need any missing datasets that are required to run the
                # `filtered_pipeline` pipeline, including any chains of missing datasets.
                unregistered_ds = pipelines[name].datasets() - set(io.list())
                output_to_unregistered = pipelines[name].only_nodes_with_outputs(
                    *unregistered_ds)
                input_from_unregistered = filtered_pipeline.inputs() & unregistered_ds
                filtered_pipeline += output_to_unregistered.to_outputs(
                    *input_from_unregistered)
            else:
                filtered_pipeline = pipelines[name].filter(
                    tags=tags,
                    from_nodes=from_nodes,
                    to_nodes=to_nodes,
                    node_names=node_names,
                    from_inputs=from_inputs,
                    to_outputs=to_outputs,
                    node_namespace=node_namespace,
                )

            p = self.db.read(id=id)
            p.status[-1].filtered_nodes = [node.name for node in filtered_pipeline.nodes]
            self.db.update(p)

            run_result = runner().run(filtered_pipeline, catalog=io,
                                      hook_manager=hook_manager, session_id=session.session_id)

            hook_manager.hook.after_pipeline_run(
                run_params=record_data,
                run_result=run_result,
                pipeline=pipelines.get(name, None),
                catalog=io
            )

            return "success"
        except Exception as e:
            logger.exception(f"Error running pipeline: {e}")
            hook_manager.hook.on_pipeline_error(
                error=e,
                run_params=record_data,
                pipeline=pipelines.get(name, None),
                catalog=io
            )
            raise e

