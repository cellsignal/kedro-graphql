"""Mongo-backed status snapshots, independent of runner and log transports."""
import asyncio
import json

import strawberry
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool

from .exceptions import InvalidPipeline
from .logs.logger import logger
from .models import PipelineStatus, State
from .pipeline_service import _reconcile_external
from .run_state import TERMINAL_STATES


@strawberry.type
class DatasetExistence:
    name: str
    config: str
    exists: bool | None


@strawberry.type
class PipelineUpdate:
    id: str
    status: list[PipelineStatus]
    datasets: list[DatasetExistence]


async def dataset_existence(dataset):
    try:
        return DatasetExistence(name=dataset.name, config=dataset.config, exists=await run_in_threadpool(dataset.exists))
    except Exception:
        logger.exception("Dataset existence check failed dataset=%s", dataset.name)
        return DatasetExistence(name=dataset.name, config=dataset.config, exists=None)


async def pipeline_updates(services, id):
    previous = None
    datasets = []
    checked_run = None
    while True:
        pipeline = await services.backend.read(id=id)
        if pipeline is None:
            raise InvalidPipeline(f"Pipeline {id} does not exist in the project.")
        current = pipeline.current_status
        run = (len(pipeline.status), current.task_id, current.state)
        if previous is None or current.state not in TERMINAL_STATES or run != checked_run:
            # ponytail: sequential storage checks bound load; add bounded concurrency if large catalogs need it.
            datasets = [await dataset_existence(dataset) for dataset in pipeline.data_catalog]
            checked_run = run
        snapshot = PipelineUpdate(id=str(pipeline.id), status=pipeline.status, datasets=datasets)
        encoded = jsonable_encoder(snapshot)
        if encoded != previous:
            previous = encoded
            yield snapshot
        await asyncio.sleep(2)


async def reconcile_active_pipelines(services):
    """Recover external run state even when no client reads the pipeline."""
    query = json.dumps({"$expr": {"$in": [
        {"$arrayElemAt": ["$status.state", -1]},
        [State.READY.value, State.STARTED.value, State.RETRY.value, State.ABORTING.value],
    ]}})
    while True:
        try:
            pipelines = await services.backend.list(limit=0, filter=query)
            for pipeline in pipelines:
                try:
                    await _reconcile_external(services, pipeline)
                except Exception:
                    logger.exception("External reconciliation failed pipeline_id=%s", pipeline.id)
        except Exception:
            logger.exception("Unable to list active pipelines for reconciliation")
        await asyncio.sleep(5)
