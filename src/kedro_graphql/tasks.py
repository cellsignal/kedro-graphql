import json
import logging
import billiard # celery's multiprocessing fork
import os
import queue
import shutil
import signal
import time
import traceback
from typing import Dict, List, Mapping

from celery import shared_task
from celery.contrib.abortable import AbortableTask
from kedro import __version__ as kedro_version
from kedro.framework.hooks import _create_hook_manager
from kedro.framework.project import pipelines
from kedro_graphql.logs.logger import KedroGraphQLLogHandler
from kedro_graphql.logs.json_log_formatter import JSONFormatter
from kedro_graphql import __version__ as kedro_graphql_version
from kedro_graphql.utils import run_sync
from kedro_graphql.runners import ExternalRunnerAborted, get_runner_class, has_external_lifecycle, init_runner
from kedro_graphql.pipeline_config import (
    build_catalog,
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
from kedro_graphql.hooks import (
    LOCAL_HOOK_CALLBACKS,
    hook_manager_for,
    remote_hook_specs_for,
)
from kedro_graphql.project import create_pipeline_session

from .archive import (
    AttemptArchive,
    PipelineTaskContextFilter,
    sanitize_config,
    utc_now,
)
from .models import State
from .run_state import InvalidRunTransition, transition_run
from .client import PIPELINE_GQL

from cloudevents.pydantic.v1 import CloudEvent
from cloudevents.conversion import from_json, to_json

logger = logging.getLogger(__name__)


def _status_metadata(status) -> dict[str, str]:
    return {item.key: item.value for item in status.metadata}


def _initial_manifest(pipeline, task_id, args, kwargs) -> dict:
    serial = pipeline.to_kedro()
    status = pipeline.current_status
    return {
        "schema_version": 1,
        "pipeline_id": str(pipeline.id),
        "task_id": task_id,
        "celery_task_id": task_id,
        "pipeline_name": pipeline.name,
        "selected_nodes": list(status.filtered_nodes) or None,
        "configuration": sanitize_config(
            {
                "data_catalog": serial["data_catalog"],
                "parameters": serial["parameters"],
            }
        ),
        "versions": {
            "kedro": kedro_version,
            "kedro_graphql": kedro_graphql_version,
            "project": getattr(pipeline, "project_version", None),
            "pipeline": getattr(pipeline, "pipeline_version", None),
        },
        "runner": status.runner,
        "runner_metadata": _status_metadata(status),
        "requested": sanitize_config({"args": args, "kwargs": kwargs}),
        "created_at": utc_now(),
        "started_at": status.started_at.isoformat() if status.started_at else None,
        "finished_at": None,
        "outcome": None,
    }


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

    def _attempt_archives(self):
        archives = getattr(self, "_archives", None)
        if archives is None:
            archives = self._archives = {}
        return archives

    def _update_current(self, pipeline, expected_state, task_id, action):
        if pipeline.current_status.task_id != task_id:
            logger.warning(
                "Skipped stale pipeline update action=%s pipeline_id=%s task_id=%s current_task_id=%s",
                action,
                pipeline.id,
                task_id,
                pipeline.current_status.task_id,
            )
            return None
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
        if pipeline.current_status.task_id != celery_task_id:
            logger.warning(
                "Skipped stale pipeline transition target=%s pipeline_id=%s task_id=%s current_task_id=%s",
                target.value,
                pipeline_id,
                celery_task_id,
                pipeline.current_status.task_id,
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

    def _persist_filtered_nodes(
        self, pipeline_id: str, task_id: str, node_names: List[str]
    ):
        pipeline = run_sync(self.db.read(id=pipeline_id))
        if pipeline is None:
            logger.warning(
                "Pipeline missing while persisting filtered nodes pipeline_id=%s task_id=%s",
                pipeline_id,
                task_id,
            )
            return None
        expected_state = pipeline.current_status.state
        pipeline.current_status.filtered_nodes = node_names
        return self._update_current(
            pipeline, expected_state, task_id, "filtered nodes"
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
        pipeline_id = kwargs["id"]
        p = run_sync(self.db.read(id=pipeline_id))
        if p is None or p.current_status.task_id != task_id:
            logger.warning(
                "Skipped stale task before_start pipeline_id=%s task_id=%s current_task_id=%s",
                pipeline_id,
                task_id,
                p.current_status.task_id if p is not None else None,
            )
            return

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
            pipeline_id,
            task_id,
            State.STARTED,
            task_id=task_id,
            task_args=json.dumps(args),
            task_kwargs=json.dumps(kwargs),
        )
        if p is None:
            root_logger.removeHandler(stream_handler)
            stream_handler.close()
            return

        try:
            task_log_dir = os.path.join(self.gql_config.log_tmp_dir, task_id)
            os.makedirs(task_log_dir, exist_ok=True)
            context_filter = PipelineTaskContextFilter(str(p.id), task_id)
            info_handler = logging.FileHandler(os.path.join(task_log_dir, "info.log"), "a")

            info_handler.setLevel(logging.INFO)
            info_handler.setFormatter(JSONFormatter())
            info_handler.addFilter(context_filter)
            error_handler = logging.FileHandler(os.path.join(task_log_dir, "errors.log"), "a")

            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JSONFormatter())
            error_handler.addFilter(context_filter)
            info_handler.kedro_graphql_task_id = task_id
            error_handler.kedro_graphql_task_id = task_id
            root_logger.addHandler(info_handler)
            root_logger.addHandler(error_handler)

            archive = None
            if self.gql_config.log_path_prefix:
                archive = AttemptArchive(
                    self.gql_config.log_path_prefix,
                    str(p.id),
                    task_id,
                    task_log_dir,
                )
                self._attempt_archives()[task_id] = archive
                archive.start_attempt(_initial_manifest(p, task_id, args, kwargs))

            logger.info(
                f"Storing tmp logs in {os.path.join(self.gql_config.log_tmp_dir, task_id)}")
            if archive is not None and archive.failed:
                logger.error(
                    "Preserving local task logs because attempt archive failed "
                    "pipeline_id=%s task_id=%s",
                    p.id,
                    task_id,
                )
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

    def _remove_task_handlers(self, task_id):
        root_logger = logging.getLogger()
        handlers_to_remove = [
            handler
            for handler in list(root_logger.handlers)
            if getattr(handler, "kedro_graphql_task_id", None) == task_id
        ]
        for handler in handlers_to_remove:
            try:
                handler.flush()
            except Exception:
                pass

            if isinstance(handler, KedroGraphQLLogHandler):
                try:
                    handler.broker.connection.delete(task_id)
                    handler.broker.connection.close()
                except Exception:
                    pass

            handler.close()
            root_logger.removeHandler(handler)

    def _finish_attempt(
        self, status, retval, task_id, kwargs, einfo, pipeline=None
    ):
        archive = self._attempt_archives().get(task_id)
        self._remove_task_handlers(task_id)

        if archive is not None:
            current = pipeline
            if current is None or current.current_status.task_id != task_id:
                current = run_sync(self.db.read(id=kwargs["id"]))
            same_task = (
                current is not None and current.current_status.task_id == task_id
            )
            outcome = current.current_status.state.value if same_task else "STALE"
            state_finished_at = (
                current.current_status.finished_at.isoformat()
                if same_task and current.current_status.finished_at
                else None
            )
            error = (
                str(retval)
                if outcome in {State.FAILURE.value, State.RETRY.value}
                else None
            )
            archive.finalize(
                outcome=outcome,
                finished_at=state_finished_at,
                worker_finished_at=utc_now(),
                error=error,
                traceback=getattr(einfo, "traceback", None),
                celery_status=str(status),
            )
            if archive.failed:
                logger.error(
                    "Preserving local task logs because attempt archive failed "
                    "pipeline_id=%s task_id=%s",
                    archive.pipeline_id,
                    task_id,
                )

        task_log_dir = os.path.join(self.gql_config.log_tmp_dir, task_id)
        retain_for_retry = status == State.RETRY.value
        if archive is not None and retain_for_retry:
            logger.info("Retaining task logs for retry task_id=%s path=%s", task_id, task_log_dir)
        elif archive is None or not archive.failed:
            try:
                shutil.rmtree(task_log_dir)
            except Exception as error:
                logger.info("Failed to clear logs in %s: %s", task_log_dir, error)
        else:
            logger.warning("Retaining task logs for archive recovery path=%s", task_log_dir)
        self._attempt_archives().pop(task_id, None)

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

        if retval == "aborted":
            pipeline = run_sync(self.db.read(id=kwargs["id"]))
            if pipeline is not None and has_external_lifecycle(
                pipeline.current_status.runner
            ):
                return
            target = State.ABORTED
        else:
            target = State.SUCCESS
        self._transition(kwargs["id"], task_id, target, task_result=str(retval))

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

        pipeline = self._transition(
            kwargs["id"],
            task_id,
            State.RETRY,
            task_exception=str(exc),
            task_einfo=str(einfo),
        )
        self._finish_attempt(
            State.RETRY.value, exc, task_id, kwargs, einfo, pipeline=pipeline
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
        if (
            p is not None
            and p.current_status.task_id == task_id
            and p.current_status.state is State.ABORTING
            and not has_external_lifecycle(p.current_status.runner)
        ):
            self._transition(
                kwargs["id"], task_id, State.ABORTED, task_result=str(retval)
            )
            p = run_sync(self.db.read(id=kwargs["id"]))

        self._finish_attempt(status, retval, task_id, kwargs, einfo, pipeline=p)


def _run_pipeline_in_child_process(
    runner: str,
    runner_kwargs: dict,
    pipeline_name: str,
    node_names: List[str],
    catalog_config: dict,
    parameters: dict,
    hook_names: List[str],
    session_id: str,
    record_data: dict,
    pipeline_id: str,
    task_id: str,
    runner_metadata: Mapping[str, str],
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

    try:
        external_runner = has_external_lifecycle(runner)
        celery_hook_manager = (
            hook_manager_for(hook_names, callbacks=LOCAL_HOOK_CALLBACKS)
            if external_runner
            else hook_manager_for(hook_names)
        )
        runner_hook_manager = (
            _create_hook_manager() if external_runner else celery_hook_manager
        )
        runner_instance = init_runner(runner_import_path=runner, **runner_kwargs)
        if external_runner:
            runner_instance.remote_hook_specs = remote_hook_specs_for(hook_names)
        runner_instance.emit_metadata = emit_metadata
        runner_instance.run_context = {
            "pipeline_id": pipeline_id,
            "task_id": task_id,
            "pipeline_name": pipeline_name,
            "metadata": dict(runner_metadata),
        }
        filtered_pipeline = pipelines[pipeline_name].only_nodes(*node_names)
        # Recreate catalog in child process to avoid fork-unsafe connections with S3.
        io = build_catalog(catalog_config, parameters)
        celery_hook_manager.hook.after_catalog_created(
            catalog=io,
            conf_catalog=None,
            conf_creds=None,
            feed_dict=None,
            save_version=None,
            load_versions=None,
        )
        celery_hook_manager.hook.before_pipeline_run(
            run_params=record_data,
            pipeline=filtered_pipeline,
            catalog=io,
        )
        run_result = runner_instance.run(
            filtered_pipeline,
            catalog=io,
            hook_manager=runner_hook_manager,
            session_id=session_id,
        )
    except BaseException as error:
        child_error = error
        child_traceback = traceback.format_exc()
        outcome = State.ABORTED if abort_triggered or isinstance(error, ExternalRunnerAborted) else State.FAILURE
    finally:
        if io is not None:
            try:
                if outcome is State.SUCCESS:
                    celery_hook_manager.hook.after_pipeline_run(
                        run_params=record_data,
                        run_result=run_result,
                        pipeline=filtered_pipeline,
                        catalog=io,
                    )
                else:
                    celery_hook_manager.hook.on_pipeline_error(
                        error=child_error,
                        run_params=record_data,
                        pipeline=filtered_pipeline,
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
                 id: str,
                 slices: List[Dict[str, List[str]]] = None,
                 only_missing: bool = False):

    p = run_sync(self.db.read(id=id))
    if p is None:
        logger.warning(
            "Pipeline id=%s not found in backend during run_pipeline; task_id=%s",
            id,
            self.request.id,
        )
        return
    if p.current_status.task_id != self.request.id:
        logger.warning(
            "Skipping stale task body pipeline_id=%s task_id=%s current_task_id=%s",
            id,
            self.request.id,
            p.current_status.task_id,
        )
        return "aborted"
    if p.current_status.state is State.ABORTING:
        return "aborted"
    serial = p.to_kedro()
    name = p.name
    parameters = serial["parameters"]
    catalog = serial["data_catalog"]
    runner = p.current_status.runner
    hook_names = list(dict.fromkeys(p.hooks))

    with create_pipeline_session(
        self.app.kedro_project_path, self.gql_config, name
    ) as session:

        logger.info("Pipeline id=%s will execute with Kedro hooks: %s", id, hook_names)
        expected_state = p.current_status.state
        p.current_status.session = session.session_id
        p = self._update_current(p, expected_state, self.request.id, "session")
        if p is None:
            return "aborted"
        if p.current_status.task_id != self.request.id:
            logger.warning(
                "Skipping stale task after session update pipeline_id=%s task_id=%s current_task_id=%s",
                id,
                self.request.id,
                p.current_status.task_id,
            )
            return "aborted"

        try:
            filters = pipeline_slice_args(slices)

            record_data = {
                "pipeline_id": id,
                "task_id": self.request.id,
                "session_id": session.session_id,
                "celery_task_id": self.request.id,
                "log_tmp_dir": self.gql_config.log_tmp_dir,
                "log_path_prefix": self.gql_config.log_path_prefix,
                "project_path": self.app.kedro_project_path.as_posix(),
                "env": self.gql_config.env,
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
                "runner": runner,
            }

            runner_kwargs = parameters.get("runner_kwargs", {})

            logger.info("Preparing runner %s with kwargs: %s", runner, runner_kwargs)
            runner_class = get_runner_class(runner)

            # Filter the pipeline based on the slices and only_missing parameters
            if only_missing:
                planning_catalog = build_catalog(catalog, parameters)
                filtered_pipeline = filter_only_missing_pipeline(
                    pipelines[name], planning_catalog
                )
            else:
                filtered_pipeline = filter_pipeline(
                    pipelines[name], slices
                )

            validate_pipeline_config(
                filtered_pipeline,
                catalog,
                parameters,
                getattr(runner_class, "supports_memory_datasets", True),
            )
            p = self._persist_filtered_nodes(
                id,
                self.request.id,
                [node.name for node in filtered_pipeline.nodes],
            )
            if p is None:
                return "aborted"

            selected_nodes = [node.name for node in filtered_pipeline.nodes]
            runner_metadata = _status_metadata(p.current_status)
            archive = self._attempt_archives().get(self.request.id)
            if archive is not None:
                archive.update(
                    selected_nodes=selected_nodes,
                    configuration=sanitize_config(
                        {"data_catalog": catalog, "parameters": parameters}
                    ),
                    execution=record_data,
                    runner_metadata=runner_metadata,
                )

            # Use Celery's multiprocessing library (billiard) instead of multiprocessing
            # to avoid AssertionError: daemonic processes are not allowed to have children
            ctx = billiard.get_context("fork")

            # queue to communicate with the child process
            result_queue = ctx.Queue()
            child = ctx.Process(
                target=_run_pipeline_in_child_process,
                args=(
                    runner,
                    runner_kwargs,
                    name,
                    [node.name for node in filtered_pipeline.nodes],
                    catalog,
                    parameters,
                    hook_names,
                    session.session_id,
                    record_data,
                    id,
                    self.request.id,
                    runner_metadata,
                    self._app.conf["broker_url"],
                    result_queue,
                ),
            )
            child.start()

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
                nonlocal child_result, runner_metadata
                if len(event) == 2 and event[0] == "metadata":
                    runner_metadata.update(event[1])
                    if archive is not None:
                        archive.update(runner_metadata=runner_metadata)
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

            outcome, error_message, child_traceback = child_result
            if outcome is State.ABORTED:
                return "aborted"
            if outcome is not State.SUCCESS:
                error_message = error_message or "Unknown child process error"
                if child_traceback:
                    error_message += f"\n\nChild process traceback:\n{child_traceback}"
                raise RuntimeError(error_message)

            return "success"
        except Exception as e:
            logger.exception(f"Error running pipeline: {e}")
            raise
