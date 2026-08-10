from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING, Any

from celery.contrib.abortable import AbortableAsyncResult
from celery.states import UNREADY_STATES
from fastapi.encoders import jsonable_encoder

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
    normalize_pipeline_config,
    validate_pipeline_config,
)
from .runners import get_runner_class
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
    catalog, parameters, sources = normalize_pipeline_config(
        full_pipeline, submitted_catalog, submitted_parameters
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
        parameter for parameter in pipeline.parameters if parameter.name in parameters
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


def _ready_status(runner: str, started_at: datetime) -> PipelineStatus:
    return PipelineStatus(
        state=State.READY,
        runner=runner,
        started_at=started_at,
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
    pipeline = Pipeline.from_dict(values)
    pipeline.hooks = _effective_hooks(services, pipeline_input.hooks)
    runner = values.get("runner") or services.config.runner
    pipeline = _normalize_pipeline(
        pipeline,
        services,
        values.get("slices"),
        values.get("only_missing", False),
        runner,
        validate=validate_ready and requested_state is PipelineInputStatus.READY,
    )
    pipeline.created_at = datetime.now()
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
    pipeline: Pipeline, values: dict[str, Any], runner: str
):
    serial = pipeline.to_kedro()
    return run_pipeline.delay(
        id=str(pipeline.id),
        name=serial["name"],
        parameters=serial["parameters"],
        data_catalog=serial["data_catalog"],
        runner=runner,
        slices=values.get("slices"),
        only_missing=values.get("only_missing", False),
        hooks=pipeline.hooks,
    )


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
        pipeline = await services.backend.create(pipeline)
        if unique_paths:
            pipeline = generate_unique_paths(pipeline, unique_paths)
            pipeline = await services.backend.update(pipeline)
        logger.info(
            "user=%s, action=create_pipeline, id=%s, name=%s, state=STAGED",
            _caller_name(caller),
            pipeline.id,
            pipeline.name,
        )
        return pipeline

    pipeline.status.append(_ready_status(runner, pipeline.created_at))
    if dry_run:
        return pipeline
    pipeline = await services.backend.create(pipeline)
    if unique_paths:
        pipeline = generate_unique_paths(pipeline, unique_paths)
        pipeline = await services.backend.update(pipeline)
    result = _publish_pipeline(pipeline, values, runner)
    logger.info(
        "user=%s, action=create_pipeline, id=%s, name=%s, state=READY, task_id=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
        result.task_id,
    )
    return pipeline


async def abort_pipeline(
    services: AppServices,
    id: str,
    caller: Mapping[str, Any] | None,
    dry_run: bool = False,
) -> Pipeline:
    pipeline = await _read_pipeline(services, id)
    current = pipeline.status[-1]
    if current.state in {State.ABORTED, State.ABORTING}:
        return pipeline
    if current.state.value not in UNREADY_STATES.union({"READY"}):
        raise InvalidPipeline(
            f"Pipeline {id} is not currently running and cannot be aborted."
        )
    if not current.task_id:
        raise InvalidPipeline(
            f"Pipeline {id} is running but has no task_id; abort is not possible."
        )
    current.state = State.ABORTING
    current.abort_requested_at = datetime.now()
    if dry_run:
        return pipeline
    AbortableAsyncResult(current.task_id, app=services.celery).abort()
    pipeline = await services.backend.update(pipeline)
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
    if requested_state is PipelineInputStatus.ABORTED:
        return await abort_pipeline(services, id, caller, dry_run)

    pipeline = await _read_pipeline(services, id)
    runner = values.get("runner") or services.config.runner
    submitted = _normalize_pipeline(
        Pipeline.from_dict(values),
        services,
        values.get("slices"),
        values.get("only_missing", False),
        runner,
        validate=requested_state is PipelineInputStatus.READY,
    )
    pipeline.parameters = submitted.parameters
    pipeline.data_catalog = submitted.data_catalog
    pipeline.tags = submitted.tags
    pipeline.parent = values.get("parent")
    pipeline.hooks = _effective_hooks(services, pipeline_input.hooks)

    if unique_paths:
        pipeline = generate_unique_paths(pipeline, unique_paths)

    current_state = pipeline.status[-1].state.value
    active_states = UNREADY_STATES.union({"READY"})
    if requested_state is PipelineInputStatus.READY and current_state not in active_states:
        if current_state == "STAGED":
            pipeline.status[-1] = _ready_status(runner, datetime.now())
        else:
            pipeline.status.append(_ready_status(runner, datetime.now()))
        if dry_run:
            return pipeline
        pipeline = await services.backend.update(pipeline)
        result = _publish_pipeline(pipeline, values, runner)
        logger.info(
            "user=%s, action=run_pipeline, id=%s, name=%s, state=READY, task_id=%s",
            _caller_name(caller),
            pipeline.id,
            pipeline.name,
            result.task_id,
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
    pipeline = await services.backend.update(pipeline)
    logger.info(
        "user=%s, action=update_pipeline, id=%s, name=%s",
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
    pipeline.status.append(_ready_status(runner, pipeline.created_at))
    pipeline = await services.backend.create(pipeline)
    pipeline.parameters.append(Parameter.from_value("id", str(pipeline.id)))
    pipeline = _normalize_pipeline(
        pipeline,
        services,
        values.get("slices"),
        values.get("only_missing", False),
        runner,
        validate=True,
    )
    pipeline = await services.backend.update(pipeline)
    result = _publish_pipeline(pipeline, values, runner)
    logger.info(
        "user=%s, action=create_pipeline, id=%s, name=%s, state=READY, task_id=%s",
        _caller_name(caller),
        pipeline.id,
        pipeline.name,
        result.task_id,
    )
    return pipeline
