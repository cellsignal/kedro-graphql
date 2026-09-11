from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from importlib import import_module
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from celery.contrib.abortable import AbortableAsyncResult
from celery.states import UNREADY_STATES
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool

from . import __version__ as kedro_graphql_version
from .exceptions import InvalidPipeline
from .logs.logger import logger
from .models import (
    DataSet,
    Node,
    Parameter,
    Pipeline,
    PipelineInput,
    PipelineInputStatus,
    PipelineStatus,
    State,
)
from .pipeline_config import (
    filter_pipeline,
    merge_parameters,
    normalize_pipeline_config,
    validate_configuration_boundary,
    validate_pipeline_config,
)
from .project import load_pipeline_configuration
from .runners import ExternalRunnerLifecycle, get_runner_class, init_runner
from .run_state import TERMINAL_STATES, InvalidRunTransition, transition_run
from .tasks import run_pipeline
from .utils import generate_unique_paths

if TYPE_CHECKING:
    from .asgi import AppServices


def _normalize_pipeline(
    pipeline: Pipeline,
    services: AppServices,
    slices,
    only_missing: bool,
    runner: str,
    globals: Mapping[str, Any] | None = None,
    validate: bool = False,
) -> Pipeline:
    full_pipeline = services.metadata.pipelines[pipeline.name]
    selected_pipeline = filter_pipeline(full_pipeline, slices)
    pipeline.describe = selected_pipeline.describe()
    pipeline.nodes = [
        Node(name=node.name, inputs=node.inputs, outputs=node.outputs, tags=node.tags)
        for node in selected_pipeline.nodes
    ]
    submitted_catalog = {
        dataset.name: dataset.parse_config() for dataset in pipeline.data_catalog
    }
    submitted_parameters = pipeline.to_kedro()["parameters"]
    try:
        server_catalog, server_parameters = load_pipeline_configuration(
            services.metadata, services.config, pipeline.name, globals
        )
    except Exception as error:
        raise InvalidPipeline(
            f"Unable to resolve configuration for pipeline {pipeline.name}: {error}"
        ) from error
    merged_catalog = {**server_catalog, **submitted_catalog}
    merged_parameters = merge_parameters(server_parameters, submitted_parameters)
    catalog, parameters, sources = normalize_pipeline_config(
        selected_pipeline, merged_catalog, merged_parameters
    )
    parameters.update(
        {
            name: value
            for name, value in merged_parameters.items()
            if name == "runner_kwargs"
        }
    )
    validate_configuration_boundary(
        catalog, parameters, services.config.pipeline_submission_max_bytes
    )

    datasets = {dataset.name: dataset for dataset in pipeline.data_catalog}
    pipeline.data_catalog = [
        DataSet(
            name=name,
            config=json.dumps(config),
            tags=list(datasets[sources[name]].tags) if sources[name] in datasets else [],
        )
        for name, config in catalog.items()
    ]
    pipeline.parameters = [
        Parameter.from_value(name, value) for name, value in sorted(parameters.items())
    ]

    if validate and not only_missing:
        runner_class = get_runner_class(runner)
        validate_pipeline_config(
            selected_pipeline,
            catalog,
            parameters,
            getattr(runner_class, "supports_memory_datasets", True),
        )
    return pipeline


def _effective_hooks(services: AppServices, hooks: list[str]) -> list[str]:
    unknown = sorted(set(hooks) - services.available_hooks)
    if unknown:
        raise InvalidPipeline(f"Unavailable pipeline hooks: {unknown}")
    return list(dict.fromkeys([*services.config.always_hooks, *hooks]))


def _caller_name(caller: Mapping[str, Any] | None) -> Any:
    if not caller:
        return None
    return caller.get("email") or caller.get("user")


async def _read_pipeline(services: AppServices, id: str) -> Pipeline:
    try:
        pipeline = await services.backend.read(id=id)
        if pipeline is None:
            raise InvalidPipeline(f"Pipeline {id} does not exist in the project.")
    except Exception as error:
        raise InvalidPipeline(f"Error retrieving pipeline {id}: {error}") from error
    return pipeline


def _external_runner(pipeline: Pipeline) -> ExternalRunnerLifecycle | None:
    status = pipeline.current_status
    if not status.runner or not status.task_id:
        return None
    runner_class = get_runner_class(status.runner)
    if not issubclass(runner_class, ExternalRunnerLifecycle):
        return None
    parameters = pipeline.to_kedro()["parameters"]
    runner = init_runner(
        status.runner, **(parameters.get("runner_kwargs") or {})
    )
    runner.emit_metadata = status.update_metadata
    runner.run_context = {
        "pipeline_id": str(pipeline.id),
        "task_id": status.task_id,
        "metadata": {item.key: item.value for item in status.metadata},
    }
    return runner


async def _reconcile_external(
    services: AppServices,
    pipeline: Pipeline,
    *,
    terminate: bool = False,
) -> Pipeline:
    if pipeline.current_status.state in TERMINAL_STATES:
        return pipeline
    runner = _external_runner(pipeline)
    if runner is None:
        return pipeline

    status = pipeline.current_status
    expected_state = status.state
    status_count = len(pipeline.status)
    original_metadata = [(item.key, item.value) for item in status.metadata]
    if terminate:
        await run_in_threadpool(runner.terminate)
    target = await run_in_threadpool(runner.reconcile)
    if target is not None:
        if not isinstance(target, State):
            raise InvalidPipeline("External runner reconciliation must return a State")
        try:
            transition_run(pipeline, target)
        except InvalidRunTransition as error:
            raise InvalidPipeline(str(error)) from error

    metadata = [(item.key, item.value) for item in status.metadata]
    if status.state is expected_state and metadata == original_metadata:
        return pipeline
    updated = await services.backend.update_if_current(
        pipeline, expected_state, status_count
    )
    return updated or await _read_pipeline(services, str(pipeline.id))


async def read_pipeline(services: AppServices, id: str) -> Pipeline:
    return await _reconcile_external(services, await _read_pipeline(services, id))


def _ready_status(runner: str, task_id: str | None = None) -> PipelineStatus:
    return PipelineStatus(
        state=State.READY,
        runner=runner,
        task_id=task_id,
        task_name=str(run_pipeline),
    )


def _staged_status(runner: str) -> PipelineStatus:
    return PipelineStatus(state=State.STAGED, runner=runner)


def _prepare_new_pipeline(
    services: AppServices,
    pipeline_input: PipelineInput,
    validate_ready: bool = True,
) -> tuple[Pipeline, dict[str, Any], str, PipelineInputStatus]:
    if pipeline_input.name not in services.metadata.pipelines:
        raise InvalidPipeline(
            f"Pipeline {pipeline_input.name} does not exist in the project."
        )

    values = jsonable_encoder(pipeline_input)
    requested_state = PipelineInputStatus(values["state"])
    pipeline = Pipeline.from_input(pipeline_input)
    pipeline.hooks = _effective_hooks(services, pipeline_input.hooks)
    runner = values.get("runner") or services.config.runner
    pipeline = _normalize_pipeline(
        pipeline,
        services,
        values.get("slices"),
        values.get("only_missing", False),
        runner,
        values.get("globals"),
        validate=validate_ready and requested_state is PipelineInputStatus.READY,
    )
    pipeline.created_at = datetime.now(timezone.utc)
    pipeline.project_version = services.config.project_version
    pipeline.kedro_graphql_version = kedro_graphql_version
    pipeline.pipeline_version = None
    if services.config.project_name:
        try:
            module = import_module(
                f".pipelines.{pipeline_input.name}",
                package=services.config.project_name,
            )
            pipeline.pipeline_version = getattr(module, "__version__", None)
        except Exception as error:
            logger.info("Could not find pipeline version: %s", error)
    return pipeline, values, runner, requested_state


def _publish_pipeline(
    pipeline: Pipeline, values: dict[str, Any], runner: str, task_id: str
):
    serial = pipeline.to_kedro()
    return run_pipeline.apply_async(
        kwargs={
            "id": str(pipeline.id),
            "name": serial["name"],
            "parameters": serial["parameters"],
            "data_catalog": serial["data_catalog"],
            "runner": runner,
            "slices": values.get("slices"),
            "only_missing": values.get("only_missing", False),
            "hooks": pipeline.hooks,
        },
        task_id=task_id,
    )


async def _publish_or_record_failure(
    services: AppServices,
    pipeline: Pipeline,
    values: dict[str, Any],
    runner: str,
) -> None:
    task_id = pipeline.current_status.task_id
    if not task_id:
        raise RuntimeError("A durable task ID is required before publication")
    try:
        _publish_pipeline(pipeline, values, runner, task_id)
    except Exception as error:
        transition_run(pipeline, State.FAILURE, task_exception=str(error))
        await services.backend.update_if_current(
            pipeline, State.READY, len(pipeline.status)
        )
        raise


async def create_pipeline(
    services: AppServices,
    pipeline_input: PipelineInput,
    caller: Mapping[str, Any] | None,
    unique_paths: list[str] | None = None,
    dry_run: bool = False,
) -> Pipeline:
    pipeline, values, runner, requested_state = _prepare_new_pipeline(
        services, pipeline_input
    )

    if requested_state is PipelineInputStatus.STAGED:
        pipeline.status.append(_staged_status(runner))
        if dry_run:
            return pipeline
        logger.info("Staging pipeline %s", pipeline.name)
        pipeline.id = str(ObjectId())
        if unique_paths:
            pipeline = generate_unique_paths(pipeline, unique_paths)
        pipeline = await services.backend.create(pipeline)
        logger.info(
            "user=%s, action=create_pipeline, id=%s, name=%s, state=STAGED",
            _caller_name(caller),
            pipeline.id,
            pipeline.name,
        )
        return pipeline

    task_id = str(uuid4())
    pipeline.status.append(_ready_status(runner, None if dry_run else task_id))
    if dry_run:
        return pipeline
    pipeline.id = str(ObjectId())
    if unique_paths:
        pipeline = generate_unique_paths(pipeline, unique_paths)
    pipeline = await services.backend.create(pipeline)
    await _publish_or_record_failure(services, pipeline, values, runner)
    logger.info(
        "user=%s, action=create_pipeline, id=%s, name=%s, state=READY, task_id=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
        task_id,
    )
    return pipeline


async def abort_pipeline(
    services: AppServices,
    id: str,
    caller: Mapping[str, Any] | None,
    dry_run: bool = False,
    *,
    pipeline: Pipeline | None = None,
) -> Pipeline:
    if pipeline is None:
        pipeline = await _read_pipeline(services, id)
    current = pipeline.current_status
    if current.state is State.ABORTED:
        return pipeline
    if (
        current.state is not State.ABORTING
        and current.state.value not in UNREADY_STATES.union({"READY"})
    ):
        raise InvalidPipeline(
            f"Pipeline {id} is not currently running and cannot be aborted."
        )
    if not current.task_id:
        raise InvalidPipeline(
            f"Pipeline {id} is running but has no task_id; abort is not possible."
        )
    expected_state = current.state
    try:
        changed = transition_run(pipeline, State.ABORTING)
    except InvalidRunTransition as error:
        raise InvalidPipeline(str(error)) from error
    if dry_run:
        return pipeline
    if changed:
        pipeline = await services.backend.update_if_current(
            pipeline, expected_state, len(pipeline.status)
        )
        if pipeline is None:
            pipeline = await _read_pipeline(services, id)
            if pipeline.current_status.state is not State.ABORTING:
                raise InvalidPipeline(
                    f"Pipeline {id} changed while abort was requested."
                )
        current = pipeline.current_status
    pipeline = await _reconcile_external(services, pipeline, terminate=True)
    current = pipeline.current_status
    AbortableAsyncResult(current.task_id, app=services.celery).abort()
    logger.info(
        "user=%s, action=abort_pipeline, id=%s, name=%s, task_id=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
        current.task_id,
    )
    return pipeline


async def update_pipeline(
    services: AppServices,
    id: str,
    pipeline_input: PipelineInput,
    caller: Mapping[str, Any] | None,
    unique_paths: list[str] | None = None,
    dry_run: bool = False,
) -> Pipeline:
    values = jsonable_encoder(pipeline_input)
    requested_state = PipelineInputStatus(values["state"])
    pipeline = await read_pipeline(services, id)
    if pipeline_input.name != pipeline.name:
        raise InvalidPipeline(
            f"Pipeline name cannot be changed from {pipeline.name} to {pipeline_input.name}."
        )
    if requested_state is PipelineInputStatus.ABORTED:
        return await abort_pipeline(
            services, id, caller, dry_run, pipeline=pipeline
        )

    expected_state = pipeline.current_status.state
    expected_status_count = len(pipeline.status)
    runner = values.get("runner") or services.config.runner
    submitted = _normalize_pipeline(
        Pipeline.from_input(pipeline_input),
        services,
        values.get("slices"),
        values.get("only_missing", False),
        runner,
        values.get("globals"),
        validate=requested_state is PipelineInputStatus.READY,
    )
    pipeline.parameters = submitted.parameters
    pipeline.data_catalog = submitted.data_catalog
    pipeline.describe = submitted.describe
    pipeline.nodes = submitted.nodes
    pipeline.tags = submitted.tags
    pipeline.parent = values.get("parent")
    pipeline.hooks = _effective_hooks(services, pipeline_input.hooks)

    if unique_paths:
        pipeline = generate_unique_paths(pipeline, unique_paths)

    current_state = pipeline.current_status.state.value
    active_states = UNREADY_STATES.union({"READY"})
    if requested_state is PipelineInputStatus.READY and current_state not in active_states:
        task_id = str(uuid4())
        if current_state == "STAGED":
            transition_run(
                pipeline,
                State.READY,
                runner=runner,
                task_id=None if dry_run else task_id,
                task_name=str(run_pipeline),
            )
        else:
            pipeline.status.append(
                _ready_status(runner, None if dry_run else task_id)
            )
        if dry_run:
            return pipeline
        pipeline = await services.backend.update_if_current(
            pipeline, expected_state, expected_status_count
        )
        if pipeline is None:
            raise InvalidPipeline(f"Pipeline {id} changed while it was submitted.")
        await _publish_or_record_failure(services, pipeline, values, runner)
        logger.info(
            "user=%s, action=run_pipeline, id=%s, name=%s, state=READY, task_id=%s",
            _caller_name(caller),
            pipeline.id,
            pipeline.name,
            task_id,
        )
        logger.info(
            "user=%s, action=update_pipeline, id=%s, name=%s",
            _caller_name(caller),
            pipeline.id,
            pipeline.name,
        )
        return pipeline

    if (
        requested_state is PipelineInputStatus.STAGED
        and current_state not in active_states
        and current_state != "STAGED"
    ):
        pipeline.status.append(_staged_status(runner))
        logger.info("Staging pipeline %s", pipeline.name)
    if dry_run:
        return pipeline
    pipeline = await services.backend.update_if_current(
        pipeline, expected_state, expected_status_count
    )
    if pipeline is None:
        raise InvalidPipeline(f"Pipeline {id} changed while it was updated.")
    logger.info(
        "user=%s, action=update_pipeline, id=%s, name=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
    )
    return pipeline


async def delete_pipeline(
    services: AppServices,
    id: str,
    caller: Mapping[str, Any] | None,
) -> Pipeline:
    pipeline = await read_pipeline(services, id)
    if pipeline.current_status.state.value in UNREADY_STATES.union(
        {"READY", "ABORTING"}
    ):
        pipeline = await abort_pipeline(services, id, caller, pipeline=pipeline)
        if pipeline.current_status.state not in TERMINAL_STATES:
            raise InvalidPipeline(
                f"Pipeline {id} termination must be confirmed before deletion."
            )
    await services.backend.delete(id=id)
    logger.info(
        "user=%s, action=delete_pipeline, id=%s, name=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
    )
    return pipeline


async def submit_event_pipeline(
    services: AppServices,
    name: str,
    event,
    caller: Mapping[str, Any] | None,
) -> Pipeline:
    pipeline_input = PipelineInput.from_event(
        name=name, event=event, state=PipelineInputStatus.READY
    )
    pipeline, values, runner, _ = _prepare_new_pipeline(
        services, pipeline_input, validate_ready=False
    )
    task_id = str(uuid4())
    pipeline.status.append(_ready_status(runner, task_id))
    pipeline.id = str(ObjectId())
    pipeline.parameters.append(Parameter.from_value("id", str(pipeline.id)))
    pipeline = _normalize_pipeline(
        pipeline,
        services,
        values.get("slices"),
        values.get("only_missing", False),
        runner,
        values.get("globals"),
        validate=True,
    )
    pipeline = await services.backend.create(pipeline)
    await _publish_or_record_failure(services, pipeline, values, runner)
    logger.info(
        "user=%s, action=create_pipeline, id=%s, name=%s, state=READY, task_id=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
        task_id,
    )
    return pipeline
