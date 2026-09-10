import json
import logging
import billiard # celery's multiprocessing fork
import os
import queue
import shutil
import signal
import time
import traceback
from datetime import date
from pathlib import Path
from typing import Dict, List, Mapping

from celery import shared_task
from celery.contrib.abortable import AbortableTask
from kedro import __version__ as kedro_version
from kedro.framework.project import pipelines
from kedro.framework.session import KedroSession
from kedro.io import AbstractDataset, DataCatalog
from omegaconf import OmegaConf

from kedro_graphql.logs.logger import KedroGraphQLLogHandler
from kedro_graphql.utils import add_param_to_feed_dict, run_sync
from kedro_graphql.runners import init_runner
from kedro_graphql.pipeline_config import (
    filter_only_missing_pipeline,
    filter_pipeline,
    pipeline_slice_args,
    validate_pipeline_config,
)
from kedro_graphql.models import (
    ParameterInput,
    Pipeline,
    PipelineInput,
    extension_metadata_entries,
)
from kedro_graphql.hooks import hook_manager_for

from .models import DataSet, State
from .run_state import InvalidRunTransition, transition_run
from .client import PIPELINE_GQL

from cloudevents.pydantic.v1 import CloudEvent
from cloudevents.conversion import from_json, to_json

logger = logging.getLogger(__name__)
class KedroGraphqlTask(AbortableTask):

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

    def _update_current(self, pipeline, expected_state, task_id, action):
        updated = run_sync(
            self.db.update_if_current(pipeline, expected_state, len(pipeline.status))
        )
        if updated is None:
            logger.warning(
                "Skipped stale pipeline update action=%s pipeline_id=%s task_id=%s",
                action,
                pipeline.id,
                task_id,
            )
        return updated

    def _transition(self, pipeline_id, celery_task_id, target, **fields):
        pipeline = run_sync(self.db.read(id=pipeline_id))
        if pipeline is None:
            logger.warning(
                "Pipeline missing during transition target=%s pipeline_id=%s task_id=%s",
                target.value,
                pipeline_id,
                celery_task_id,
            )
            return None
        expected_state = pipeline.current_status.state
        try:
            changed = transition_run(pipeline, target, **fields)
        except InvalidRunTransition as error:
            logger.warning(
                "Rejected pipeline transition pipeline_id=%s task_id=%s: %s",
                pipeline_id,
                celery_task_id,
                error,
            )
            return None
        if not changed:
            return pipeline
        return self._update_current(
            pipeline, expected_state, celery_task_id, target.value
        )

    def _persist_runner_metadata(
        self, pipeline_id: str, task_id: str, values: Mapping[str, str]
    ):
        pipeline = run_sync(self.db.read(id=pipeline_id))
        if pipeline is None:
            logger.warning(
                "Pipeline missing while persisting runner metadata pipeline_id=%s task_id=%s",
                pipeline_id,
                task_id,
            )
            return None
        expected_state = pipeline.current_status.state
        pipeline.current_status.update_metadata(values)
        return self._update_current(
            pipeline, expected_state, task_id, "runner metadata"
        )

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
        root_logger = logging.getLogger()
        # Attach a task-scoped Redis stream handler so all propagated logs can be
        # consumed by the `pipelineLogs` GraphQL subscription for this task.
        stream_handler = KedroGraphQLLogHandler(
            task_id,
            broker_url=self._app.conf["broker_url"],
        )
        stream_handler.kedro_graphql_task_id = task_id
        root_logger.addHandler(stream_handler)
        p = self._transition(
            kwargs["id"],
            task_id,
            State.STARTED,
            task_id=task_id,
            task_args=json.dumps(args),
            task_kwargs=json.dumps(kwargs),
        )
        if p is None:
            return

        try:
            os.makedirs(os.path.join(
                self.gql_config.log_tmp_dir, task_id), exist_ok=True)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            info_handler = logging.FileHandler(os.path.join(
                self.gql_config.log_tmp_dir, task_id + '/info.log'), 'a')

            info_handler.setLevel(logging.INFO)
            info_handler.setFormatter(formatter)
            error_handler = logging.FileHandler(os.path.join(
                self.gql_config.log_tmp_dir, task_id + '/errors.log'), 'a')

            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            info_handler.kedro_graphql_task_id = task_id
            error_handler.kedro_graphql_task_id = task_id
            root_logger.addHandler(info_handler)
            root_logger.addHandler(error_handler)
            logger.info(
                f"Storing tmp logs in {os.path.join(self.gql_config.log_tmp_dir, task_id)}")

            log_path_prefix = self.gql_config.log_path_prefix
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
                    gql_meta.config)).save(p.to_kedro())
                p = self._update_current(p, State.STARTED, task_id, "log metadata")
                if p is None:
                    return

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

        self._transition(
            kwargs["id"], task_id, State.SUCCESS, task_result=str(retval)
        )

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

        self._transition(
            kwargs["id"],
            task_id,
            State.RETRY,
            task_exception=str(exc),
            task_einfo=str(einfo),
        )

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

        self._transition(
            kwargs["id"],
            task_id,
            State.FAILURE,
            task_exception=str(exc),
            task_einfo=str(einfo),
            task_result=str(exc),
        )

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

        p = run_sync(self.db.read(id=kwargs["id"]))
        if p is not None and p.current_status.state is State.ABORTING:
            self._transition(
                kwargs["id"], task_id, State.ABORTED, task_result=str(retval)
            )

        # Clean up only this task's handlers from the root logger.
        root_logger = logging.getLogger()
        handlers_to_remove = [
            h for h in list(root_logger.handlers)
            if getattr(h, "kedro_graphql_task_id", None) == task_id
        ]
        for handler in handlers_to_remove:
            try:
                handler.flush()
            except Exception:
                pass

            if isinstance(handler, KedroGraphQLLogHandler):
                try:
                    # Remove the Redis stream for this task and close connection.
                    handler.broker.connection.delete(task_id)
                    handler.broker.connection.close()
                except Exception:
                    pass

            handler.close()
            root_logger.removeHandler(handler)

        try:
            shutil.rmtree(os.path.join(
                self.gql_config.log_tmp_dir, task_id))
        except Exception as e:
            logger.info(
                f"Failed to clear logs in {os.path.join(self.gql_config.log_tmp_dir, task_id)}: {e}")


def _run_pipeline_in_child_process(
    runner_instance,
    filtered_pipeline,
    catalog_config: dict,
    parameters: dict,
    hook_manager,
    session_id: str,
    record_data: dict,
    pipeline_name: str,
    pipeline_id: str,
    task_id: str,
    broker_url: str,
    result_queue,
):
    """Execute Kedro pipeline in a child process and report result via queue."""
    try:
        # Put child in its own process group so parent can signal descendants.
        os.setsid()
    except OSError:
        pass

    # Recreate stream handler in child process so Redis connection is process-local.
    root_logger = logging.getLogger()
    handlers_to_remove = [
        h for h in list(root_logger.handlers)
        if getattr(h, "kedro_graphql_task_id", None) == task_id
        and isinstance(h, KedroGraphQLLogHandler)
    ]
    for handler in handlers_to_remove:
        try:
            handler.flush()
        except Exception:
            pass
        handler.close()
        root_logger.removeHandler(handler)

    # Recreate the stream handler in the child so Redis connection state is
    # owned by this process and safe to use after fork.
    stream_handler = KedroGraphQLLogHandler(task_id, broker_url=broker_url)
    stream_handler.kedro_graphql_task_id = task_id
    root_logger.addHandler(stream_handler)

    abort_triggered = False
    io = None
    run_result = None
    child_error = None
    child_traceback = None
    outcome = State.SUCCESS

    def handle_abort_signal(signum, frame):
        """Handle SIGINT or SIGTERM by setting flag so logs and hooks are properly cleaned up."""
        nonlocal abort_triggered
        abort_triggered = True
        # Raise KeyboardInterrupt to exit pipeline execution and trigger except block.
        raise KeyboardInterrupt("Pipeline abort signal received")

    # Register signal handlers so SIGINT/SIGTERM don't forcefully kill the child
    # before logs and hooks are flushed.
    signal.signal(signal.SIGINT, handle_abort_signal)
    signal.signal(signal.SIGTERM, handle_abort_signal)

    def emit_metadata(values: Mapping[str, str]) -> None:
        extension_metadata_entries(values)
        result_queue.put(("metadata", dict(values)))

    runner_instance.emit_metadata = emit_metadata
    runner_instance.run_context = {
        "pipeline_id": pipeline_id,
        "task_id": task_id,
    }

    try:
        # Recreate catalog in child process to avoid fork-unsafe connections with S3
        io = DataCatalog.from_config(catalog=catalog_config)
        
        # Re-add parameters to catalog
        feed_dict = {"parameters": parameters}
        for param_name, param_value in parameters.items():
            add_param_to_feed_dict(feed_dict, param_name, param_value)
        io.add_feed_dict(feed_dict)
        
        run_result = runner_instance.run(
            filtered_pipeline,
            catalog=io,
            hook_manager=hook_manager,
            session_id=session_id,
        )
    except BaseException as error:
        child_error = error
        child_traceback = traceback.format_exc()
        outcome = State.ABORTED if abort_triggered else State.FAILURE
    finally:
        if io is not None:
            try:
                if outcome is State.SUCCESS:
                    hook_manager.hook.after_pipeline_run(
                        run_params=record_data,
                        run_result=run_result,
                        pipeline=pipelines.get(pipeline_name),
                        catalog=io,
                    )
                else:
                    hook_manager.hook.on_pipeline_error(
                        error=child_error,
                        run_params=record_data,
                        pipeline=pipelines.get(pipeline_name),
                        catalog=io,
                    )
            except Exception as cleanup_error:
                logger.warning("Error during child cleanup: %s", cleanup_error)
                if outcome is State.SUCCESS:
                    outcome = State.FAILURE
                    child_error = cleanup_error
                    child_traceback = traceback.format_exc()
            for handler in list(root_logger.handlers):
                if getattr(handler, "kedro_graphql_task_id", None) == task_id:
                    try:
                        handler.flush()
                    except Exception:
                        pass
                    handler.close()
                    root_logger.removeHandler(handler)
        result_queue.put(
            (outcome, str(child_error) if child_error else None, child_traceback)
        )

@shared_task(bind=True, base=KedroGraphqlTask)
def run_pipeline(self,
                 id: str = None,
                 name: str = None,
                 parameters: dict = None,
                 data_catalog: dict = None,
                 runner: str = None,
                 slices: List[Dict[str, List[str]]] = None,
                 only_missing: bool = False,
                 hooks: List[str] = None):

    with KedroSession.create(project_path=Path(__file__).resolve().parent.parent.parent,
                             env=self.gql_config.env,
                             conf_source=self.gql_config.conf_source) as session:

        hook_names = list(dict.fromkeys(hooks or []))
        try:
            hook_manager = hook_manager_for(hook_names)
        except ValueError as error:
            raise RuntimeError(f"Unable to resolve pipeline hooks: {error}") from error
        logger.info("Pipeline id=%s will execute with Kedro hooks: %s", id, hook_names)
        session._hook_manager = hook_manager

        p = run_sync(self.db.read(id=id))
        if p is None:
            logger.warning(
                "Pipeline id=%s not found in backend during run_pipeline; task_id=%s",
                id,
                self.request.id,
            )
            return
        expected_state = p.current_status.state
        p.current_status.session = session.session_id
        if self._update_current(p, expected_state, self.request.id, "session") is None:
            return

        # If modified data catalog object with gql_meta and gql_logs datasets exists, use it
        if getattr(self, "kedro_graphql_pipeline", None):
            logger.info("using data_catalog with gql_meta and gql_logs")
            serial = self.kedro_graphql_pipeline.to_kedro()
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
            filters = pipeline_slice_args(slices)

            record_data = {
                "session_id": session.session_id,
                "celery_task_id": self.request.id,
                "log_tmp_dir": self.gql_config.log_tmp_dir,
                "log_path_prefix": self.gql_config.log_path_prefix,
                "project_path": session._project_path.as_posix(),
                "env": session.load_context().env,
                "kedro_version": kedro_version,
                # Construct the pipeline using only nodes which have this tag attached.
                "tags": filters.get("tags"),
                # A list of node names which should be used as a starting point.
                "from_nodes": filters.get("from_nodes"),
                # A list of node names which should be used as an end point.
                "to_nodes": filters.get("to_nodes"),
                "node_names": filters.get("node_names"),
                # A list of dataset names which should be used as a starting point.
                "from_inputs": filters.get("from_inputs"),
                # A list of dataset names which should be used as an end point.
                "to_outputs": filters.get("to_outputs"),
                # Specify a particular dataset version (timestamp) for loading
                "load_versions": "",
                # Specify extra parameters that you want to pass to the context initialiser.
                "extra_params": "",
                "pipeline_name": name,
                "namespace": filters.get("node_namespace"),
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

            runner_kwargs = conf_parameters.get("runner_kwargs", {})

            logger.info(f"Initializing runner {runner} with kwargs: {runner_kwargs}")
            runner_instance = init_runner(runner_import_path=runner, **runner_kwargs)

            # Filter the pipeline based on the slices and only_missing parameters
            if only_missing:
                filtered_pipeline = filter_only_missing_pipeline(pipelines[name], io)
            else:
                filtered_pipeline = filter_pipeline(
                    pipelines[name], slices
                )

            validate_pipeline_config(
                filtered_pipeline,
                catalog,
                parameters,
                getattr(runner_instance, "supports_memory_datasets", True),
            )
            hook_manager.hook.before_pipeline_run(
                run_params=record_data,
                pipeline=filtered_pipeline,
                catalog=io,
            )

            p = run_sync(self.db.read(id=id))
            expected_state = p.current_status.state
            p.current_status.filtered_nodes = [node.name for node in filtered_pipeline.nodes]
            if self._update_current(
                p, expected_state, self.request.id, "filtered nodes"
            ) is None:
                return

            # Use Celery's multiprocessing library (billiard) instead of multiprocessing
            # to avoid AssertionError: daemonic processes are not allowed to have children
            ctx = billiard.get_context("fork")

            # queue to communicate with the child process
            result_queue = ctx.Queue()
            child = ctx.Process(
                target=_run_pipeline_in_child_process,
                args=(
                    runner_instance,
                    filtered_pipeline,
                    catalog,
                    conf_parameters,
                    hook_manager,
                    session.session_id,
                    record_data,
                    name,
                    id,
                    self.request.id,
                    self._app.conf["broker_url"],
                    result_queue,
                ),
            )
            child.start()
            child_owns_terminal_hook = True

            polling_interval = self.gql_config.celery_abort_polling_interval
            if polling_interval < 1:
                logger.warning(
                    "KEDRO_GRAPHQL_CELERY_ABORT_POLLING_INTERVAL=%s is below minimum 1s; clamping to 1s",
                    polling_interval,
                )
                polling_interval = 1.0
            grace_period = self.gql_config.celery_abort_grace_period
            if grace_period < 5:
                logger.warning(
                    "KEDRO_GRAPHQL_CELERY_ABORT_GRACE_PERIOD=%s is below minimum 5s; clamping to 5s",
                    grace_period,
                )
                grace_period = 5.0
            
            sigint_sent_at = None
            sigterm_sent_at = None
            child_result = None

            def consume_child_event(event):
                nonlocal child_result
                if len(event) == 2 and event[0] == "metadata":
                    self._persist_runner_metadata(id, self.request.id, event[1])
                else:
                    child_result = event

            while child.is_alive():
                if self.is_aborted():
                    now = time.monotonic()
                    if sigint_sent_at is None:
                        logger.info("Abort requested for task=%s; sending SIGINT to child pid=%s", self.request.id, child.pid)
                        try:
                            child_pgid = os.getpgid(child.pid)
                            # there could be a small window where the child process doesn't yet have its own process group
                            # so we ensure we don't signal the parent process group
                            if child_pgid == os.getpgrp():
                                # send SIGINT to the child process directly
                                os.kill(child.pid, signal.SIGINT)
                            else:
                                # send SIGINT to the child process's process group
                                os.killpg(child_pgid, signal.SIGINT)
                        except ProcessLookupError:
                            pass
                        sigint_sent_at = now
                    elif now - sigint_sent_at >= grace_period and sigterm_sent_at is None:
                        logger.warning("Child pid=%s did not exit after SIGINT; escalating to SIGTERM", child.pid)
                        try:
                            child_pgid = os.getpgid(child.pid)
                            if child_pgid == os.getpgrp():
                                os.kill(child.pid, signal.SIGTERM)
                            else:
                                os.killpg(child_pgid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        sigterm_sent_at = now
                    elif sigterm_sent_at is not None and now - sigterm_sent_at >= grace_period:
                        logger.error("Child pid=%s did not exit after SIGTERM; escalating to SIGKILL", child.pid)
                        try:
                            child_pgid = os.getpgid(child.pid)
                            if child_pgid == os.getpgrp():
                                os.kill(child.pid, signal.SIGKILL)
                            else:
                                os.killpg(child_pgid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    wait_timeout = 1
                else:
                    wait_timeout = polling_interval
                try:
                    consume_child_event(result_queue.get(timeout=wait_timeout))
                except queue.Empty:
                    pass
                if child_result is not None:
                    child.join()
                    break

            child.join()
            if child_result is None:
                deadline = time.monotonic() + 1
                while child_result is None and time.monotonic() < deadline:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        consume_child_event(result_queue.get(timeout=remaining))
                    except queue.Empty:
                        break
                if child_result is None:
                    child_result = (
                        State.FAILURE,
                        "Child process exited without returning a result",
                        None,
                    )
                    logger.warning(
                        "Child process pid=%s finished without posting a result",
                        child.pid,
                    )

            if self.is_aborted():
                return "aborted"

            outcome, error_message, _ = child_result
            if outcome is not State.SUCCESS:
                raise RuntimeError(error_message or "Unknown child process error")

            return "success"
        except Exception as e:
            logger.exception(f"Error running pipeline: {e}")
            if not locals().get("child_owns_terminal_hook", False):
                hook_manager.hook.on_pipeline_error(
                    error=e,
                    run_params=record_data,
                    pipeline=pipelines.get(name, None),
                    catalog=io
                )
            raise e
