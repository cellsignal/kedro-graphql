import asyncio
from base64 import b64decode, b64encode
from datetime import datetime
from importlib import import_module
from typing import Optional, Union, List, Callable, Any
import json
from collections.abc import AsyncGenerator, Iterable
from graphql.execution import ExecutionContext as GraphQLExecutionContext

import strawberry
from bson.objectid import ObjectId
from celery.states import UNREADY_STATES, READY_STATES
from fastapi.encoders import jsonable_encoder
from kedro.framework.project import pipelines
from strawberry.extensions import SchemaExtension
from strawberry.permission import PermissionExtension
from strawberry.tools import merge_types
from strawberry.types import Info
from strawberry.directive import StrawberryDirective
from strawberry.types.base import StrawberryType
from strawberry.types.scalar import ScalarDefinition, ScalarWrapper
from strawberry.schema.config import StrawberryConfig
from strawberry.scalars import JSON
from strawberry.extensions import FieldExtension

from . import __version__ as kedro_graphql_version
from .config import load_config
from .pipeline_event_monitor import PipelineEventMonitor
from .hooks import InvalidPipeline
from .logs.logger import PipelineLogStream, logger
from .models import (
    DataSetInput,
    PageMeta,
    Pipeline,
    PipelineEvent,
    PipelineInput,
    PipelineLogMessage,
    Pipelines,
    PipelineStatus,
    PipelineTemplate,
    PipelineTemplates,
    State,
    DataSetInput
)
from .tasks import run_pipeline
from .permissions import get_permissions
from .signed_url.base import SignedUrlProvider
from .utils import generate_unique_paths

CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))
logger.info("{s} using permissions class: {d}".format(s=__name__, d=PERMISSIONS_CLASS))


def encode_cursor(id: int) -> str:
    """
    Encodes the given id into a cursor.

    :param id: The ID to encode.

    :return: The encoded cursor.
    """
    return b64encode(f"cursor:{id}".encode("ascii")).decode("ascii")


def decode_cursor(cursor: str) -> int:
    """
    Decodes the ID from the given cursor.

    :param cursor: The cursor to decode.

    :return: The decoded user ID.
    """
    cursor_data = b64decode(cursor.encode("ascii")).decode("ascii")
    return cursor_data.split(":")[1]


class DataSetConfigException(Exception):
    """``DataSetConfigException`` raised by ``DataSetConfigExtension`` implementations
    in case of failure.

    ``DataSetConfigExtensions`` implementations should provide instructive
    information in case of failure.
    """

    pass


class PipelineExtension(FieldExtension):
    """
    Intercepts Pipeline arguments to mask filepaths before returning.
    This extension should be added to any Query or Mutation that returns a Pipeline or Pipelines object.
    This extension requires the KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS config to be set to have any effect.
    """

    def resolve(
        self, next_: Callable[..., Any], source: Any, info: strawberry.Info, **kwargs
    ):
        """
        Intercepts Pipeline and Pipelines return values to mask filepaths before returning.

        Args:
            next_ (Callable[..., Any]): The next resolver in the chain.
            source (Any): The source object.
            info (strawberry.Info): The GraphQL execution context.
            **kwargs: Additional keyword arguments.

        Returns:
            Union[Pipeline, Pipelines]: The Pipeline or Pipelines object with masked filepaths.
        """
        # call original resolver
        pipeline = next_(source, info, **kwargs)

        if isinstance(pipeline, Pipeline):
            # mask filepaths before returning
            return PipelineSanitizer.mask_filepaths(
                pipeline, CONFIG["KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS"])
        elif isinstance(pipeline, Pipelines):
            pipelines = []
            for p in pipeline.pipelines:
                pipelines.append(PipelineSanitizer.mask_filepaths(
                    p, CONFIG["KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS"]))
            pipeline.pipelines = pipelines
            return pipeline


class PipelineInputExtension(FieldExtension):
    """
    Intercepts PipelineInput arguments to unmask and validate filepaths before
    passing to the resolver, then masks filepaths again before returning the Pipeline result.
    This extension should be added to any Mutation that takes a PipelineInput argument.
    This extension requires the KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS and/or KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS
    config to be set to have any effect.
    """

    def resolve(
        self, next_: Callable[..., Any], source: Any, info: strawberry.Info, **kwargs
    ):
        """
        Intercepts PipelineInput argument to unmask and validate filepaths before
        passing to the resolver, then masks filepaths again before returning the Pipeline result.

        Args:
            next_ (Callable[..., Any]): The next resolver in the chain.
            source (Any): The source object.
            info (strawberry.Info): The GraphQL execution context.
            **kwargs: Additional keyword arguments.

        Returns:
            Pipeline: The Pipeline object with masked filepaths.

        Raises:
            DataSetConfigException: If any dataset filepath does not start with allowed prefixes.
        """
        # intercept PipelineInput and sanitize filepaths
        pipeline_input = kwargs["pipeline"]

        kwargs["pipeline"] = PipelineSanitizer.unmask_filepaths(
            pipeline_input, CONFIG["KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS"])

        PipelineSanitizer.sanitize_filepaths(
            pipeline_input, CONFIG["KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS"])

        # call original resolver
        pipeline = next_(source, info, **kwargs)
        # mask filepaths again before returning
        return PipelineSanitizer.mask_filepaths(
            pipeline, CONFIG["KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS"])


class PipelineSanitizer:

    @staticmethod
    def sanitize_filepaths(pipeline: Pipeline | PipelineInput, allowed_roots: list[str]) -> None:
        """Raises DataSetConfigException if any dataset filepath does not start with any of the allowed roots.

        Args:
            pipeline (Pipeline | PipelineInput): The pipeline to sanitize.
            allowed_roots (list[str]): The list of allowed roots.
        Returns:
            None

        Raises:
            DataSetConfigException: If any dataset filepath does not start with allowed prefixes.
        """
        if pipeline.data_catalog:
            for d in pipeline.data_catalog:
                c = json.loads(d.config)
                if c.get("filepath"):
                    if len(allowed_roots) > 0 and not any(c["filepath"].startswith(root) for root in allowed_roots):
                        raise DataSetConfigException(
                            "filepath " + c["filepath"] + " not allowed")

    @classmethod
    def mask_filepaths(cls, pipeline: Pipeline | PipelineInput, masks: list[dict]) -> Pipeline | PipelineInput:
        """
        Masks filepaths in the pipeline's data catalog according to the given masks.

        Args:
            pipeline (Pipeline | PipelineInput): The pipeline to mask.
            masks (list[dict]): The list of masks.

        Returns:
            Pipeline | PipelineInput: The pipeline with masked filepaths.
        """
        if pipeline.data_catalog:
            for d in pipeline.data_catalog:
                try:
                    c = json.loads(d.config)
                    if c.get("filepath"):
                        for mask in masks:
                            if c["filepath"].startswith(mask["prefix"]):
                                c["filepath"] = c["filepath"].replace(
                                    mask["prefix"], mask["mask"])
                        d.config = json.dumps(c)

                except Exception as e:
                    logger.warning(
                        f"Could not parse config for dataset {d.name}: {e}")
        return pipeline

    @classmethod
    def unmask_filepaths(cls, pipeline: Pipeline | PipelineInput, masks: list[dict]) -> Pipeline | PipelineInput:
        """
        Unmasks filepaths in the pipeline's data catalog according to the given masks.

        Args:
            pipeline (Pipeline | PipelineInput): The pipeline to unmask.
            masks (list[dict]): The list of masks.

        Returns:
            Pipeline | PipelineInput: The pipeline with unmasked filepaths.
        """
        if pipeline.data_catalog:
            for d in pipeline.data_catalog:
                try:
                    c = json.loads(d.config)
                    if c.get("filepath"):
                        for mask in masks:
                            if c["filepath"].startswith(mask["mask"]):
                                c["filepath"] = c["filepath"].replace(
                                    mask["mask"], mask["prefix"])
                        d.config = json.dumps(c)
                except Exception as e:
                    logger.warning(
                        f"Could not parse config for dataset {d.name}: {e}")
        return pipeline


@strawberry.type
class Query:
    @strawberry.field(description="Get a pipeline template.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="read_pipeline_template")])])
    def pipeline_template(self, info: Info, id: str) -> PipelineTemplate:
        for p in info.context["request"].app.kedro_pipelines_index:
            if p.id == id:
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_pipeline_template, id={id}")
                return p

    @strawberry.field(description="Get a list of pipeline templates.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="read_pipeline_templates")])])
    def pipeline_templates(self, info: Info, limit: int, cursor: Optional[str] = None) -> PipelineTemplates:
        if cursor is not None:
            # decode the user ID from the given cursor.
            pipe_id = ObjectId(decode_cursor(cursor=cursor))
        else:
            # unix epoch Jan 1, 1970 as objectId
            pipe_id = ObjectId("100000000000000000000000")

        # filter the pipeline template data, going through the next set of results.
        filtered_data = [pipe for pipe in info.context["request"].app.kedro_pipelines_index
                         if pipe.id.generation_time >= pipe_id.generation_time]

        # slice the relevant pipeline template data (Here, we also slice an
        # additional pipe instance, to prepare the next cursor).
        sliced_pipes = filtered_data[: limit + 1]

        if len(sliced_pipes) > limit:
            # calculate the client's next cursor.
            last_pipe = sliced_pipes.pop(-1)
            next_cursor = encode_cursor(id=last_pipe.id)
        else:
            # We have reached the last page, and
            # don't have the next cursor.
            next_cursor = None
        logger.info(
            f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_pipeline_templates, limit={limit}, cursor={cursor}")
        return PipelineTemplates(
            pipeline_templates=sliced_pipes, page_meta=PageMeta(
                next_cursor=next_cursor)
        )

    @strawberry.field(description="Get a pipeline instance.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="read_pipeline")]), PipelineExtension()])
    def read_pipeline(self, id: str, info: Info) -> Pipeline:
        try:
            p = info.context["request"].app.backend.read(id=id)
            if p is None:
                raise InvalidPipeline(
                    f"Pipeline {id} does not exist in the project.")
        except Exception as e:
            raise InvalidPipeline(f"Error retrieving pipeline {id}: {e}")
        logger.info(
            f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_pipeline, id={id}")
        return p

    @strawberry.field(description="Get a list of pipeline instances.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="read_pipelines")]), PipelineExtension()])
    def read_pipelines(self, info: Info, limit: int, cursor: Optional[str] = None, filter: Optional[str] = "",
                       sort: Optional[str] = "") -> Pipelines:
        if cursor is not None:
            # decode the user ID from the given cursor.
            pipe_id = decode_cursor(cursor=cursor)
        else:
            pipe_id = "000000000000000000000000"  # unix epoch Jan 1, 1970 as objectId

        results = info.context["request"].app.backend.list(
            cursor=pipe_id, limit=limit + 1, filter=filter, sort=sort)
        if len(results) > limit:

            # calculate the client's next cursor.
            last_pipe = results.pop(-1)
            next_cursor = encode_cursor(id=last_pipe.id)
        else:
            # We have reached the last page, and
            # don't have the next cursor.
            next_cursor = None

        logger.info(
            f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_pipelines, filter={filter}, limit={limit}, sort={sort}, cursor={cursor}")
        return Pipelines(
            pipelines=results, page_meta=PageMeta(next_cursor=next_cursor)
        )

    @strawberry.field(description="Read a dataset with a signed URL", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="read_dataset")])])
    def read_datasets(self, id: str, info: Info, datasets: List[DataSetInput], expires_in_sec: int = CONFIG["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"]) -> List[str | None]:
        """
        Get a signed URL for downloading a dataset.

        Args:
            id (str): The ID of the pipeline.
            info (Info): The GraphQL execution context.
            datasets (List[DataSetInput]): The datasets to get signed URLs for. In order to read specific partitions of a PartitionedDataset, pass a DataSetInput with the dataset name and list of partitions e.g. DataSetInput(name="dataset_name", partitions=["partition1", "partition2"]).
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
        Returns:
            List[str | None]: An array of signed URLs for downloading the dataset or None if not applicable.

        Raises:
            ValueError: If expires_in_sec is greater than max expires_in_sec
            DataSetConfigError: If the dataset configuration is invalid or cannot be parsed.
            TypeError: If the signed URL provider does not inherit from SignedUrlProvider.
        """

        if expires_in_sec > CONFIG["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"]:
            raise ValueError(
                f"expires_in_sec cannot be greater than {CONFIG['KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC']} seconds ({CONFIG['KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC'] // 3600} hours)")

        urls = []
        p = info.context["request"].app.backend.read(id=id)

        catalog = {d.name: d for d in p.data_catalog}

        for d in datasets:
            dataset = catalog.get(d.name, None)
            if dataset is None:
                logger.warning(
                    f"Dataset '{d.name}' not found in the data catalog of pipeline_name={p.name} pipeline_id={p.id}. SignedURL set to None.")
                urls.append(None)
                continue

            module_path, class_name = CONFIG["KEDRO_GRAPHQL_SIGNED_URL_PROVIDER"].rsplit(
                ".", 1)
            module = import_module(module_path)
            cls = getattr(module, class_name)

            if not issubclass(cls, SignedUrlProvider):
                raise TypeError(
                    f"{class_name} must inherit from SignedUrlProvider")

            logger.info(
                f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, expires_in_sec={expires_in_sec}")
            urls.append(cls.read(info, dataset, expires_in_sec, d.partitions))

        return urls


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Execute a pipeline.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="create_pipeline")]), PipelineInputExtension()])
    def create_pipeline(self, pipeline: PipelineInput, info: Info, unique_paths: Optional[List[str]] = None) -> Pipeline:
        """
        - is validation against template needed, e.g. check DataSet type or at least check dataset names
        """

        if pipeline.name not in pipelines.keys():
            raise InvalidPipeline(
                f"Pipeline {pipeline.name} does not exist in the project.")

        d = jsonable_encoder(pipeline)
        p = Pipeline.decode(d)
        p.describe = info.context["request"].app.kedro_pipelines[p.name].describe()
        p.nodes = info.context["request"].app.kedro_pipelines[p.name].nodes
        serial = p.encode(encoder="kedro")

        runner = d.get(
            "runner") or info.context["request"].app.config["KEDRO_GRAPHQL_RUNNER"]
        # credentials not supported yet
        # merge any credentials with inputs and outputs
        # credentials are intentionally not persisted
        # NOTE celery result may persist creds in task result?

        started_at = datetime.now()
        p.created_at = started_at

        # Get kedro project, kedro-graphql, and pipeline versions
        p.project_version = CONFIG.get("KEDRO_PROJECT_VERSION", None)
        p.kedro_graphql_version = kedro_graphql_version
        p.pipeline_version = None
        package_name = CONFIG.get("KEDRO_PROJECT_NAME", None)
        if package_name:
            try:
                module = import_module(
                    f".pipelines.{pipeline.name}", package=package_name)
                p.pipeline_version = getattr(module, "__version__", None)
            except Exception as e:
                logger.info(f"Could not find pipeline version: {e}")

        if d["state"] == "STAGED":
            p.status.append(PipelineStatus(state=State.STAGED,
                                           runner=runner,
                                           session=None,
                                           started_at=None,
                                           finished_at=None,
                                           task_id=None,
                                           task_name=None))
            logger.info(f'Staging pipeline {p.name}')
            p = info.context["request"].app.backend.create(p)
            if unique_paths:
                p = generate_unique_paths(p, unique_paths)
                p = info.context["request"].app.backend.update(p)

            logger.info(
                f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=create_pipeline, id={p.id}, name={p.name}, state=STAGED")
            return p
        else:
            p.status.append(PipelineStatus(state=State.READY,
                                           runner=runner,
                                           session=None,
                                           started_at=started_at,
                                           finished_at=None,
                                           task_id=None,
                                           task_name=str(run_pipeline)))

            p = info.context["request"].app.backend.create(p)
            if unique_paths:
                p = generate_unique_paths(p, unique_paths)
                p = info.context["request"].app.backend.update(p)

            result = run_pipeline.delay(
                id=str(p.id),
                name=serial["name"],
                parameters=serial["parameters"],
                data_catalog=serial["data_catalog"],
                runner=runner,
                slices=d.get("slices", None),
                only_missing=d.get("only_missing", False)
            )

            logger.info(
                f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=create_pipeline, id={p.id}, name={p.name}, state=READY, task_id={result.task_id}")
            return p

    @strawberry.mutation(description="Update a pipeline.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="update_pipeline")]), PipelineInputExtension()])
    def update_pipeline(self, id: str, pipeline: PipelineInput, info: Info, unique_paths: Optional[List[str]] = None) -> Pipeline:

        try:
            p = info.context["request"].app.backend.read(id=id)
            if p is None:
                raise InvalidPipeline(
                    f"Pipeline {id} does not exist in the project.")
        except Exception as e:
            raise InvalidPipeline(f"Error retrieving pipeline {id}: {e}")

        pipeline_input_dict = jsonable_encoder(pipeline)

        # Update pipeline with new pipeline input
        p.parameters = pipeline_input_dict.get("parameters")
        p.data_catalog = pipeline_input_dict.get("data_catalog")
        p.tags = pipeline_input_dict.get("tags")
        p.parent = pipeline_input_dict.get("parent")
        runner = pipeline_input_dict.get(
            "runner") or info.context["request"].app.config["KEDRO_GRAPHQL_RUNNER"]

        # If PipelineInput is READY and pipeline is not already running
        if pipeline_input_dict.get("state", None) == "READY" and p.status[-1].state.value not in UNREADY_STATES.union(["READY"]):

            if (p.status[-1].state.value != "STAGED"):
                # Add new status object to pipeline because this is another run attempt
                p.status.append(PipelineStatus(state=State.READY,
                                               runner=runner,
                                               session=None,
                                               started_at=datetime.now(),
                                               finished_at=None,
                                               task_id=None,
                                               task_name=str(run_pipeline)))
            else:
                # Replace staged status with running status
                p.status[-1] = PipelineStatus(state=State.READY,
                                              runner=runner,
                                              session=None,
                                              started_at=datetime.now(),
                                              finished_at=None,
                                              task_id=None,
                                              task_name=str(run_pipeline))

            if unique_paths:
                p = generate_unique_paths(p, unique_paths)

            # Update pipeline in backend before running task
            p = info.context["request"].app.backend.update(p)

            serial = p.encode(encoder="kedro")

            result = run_pipeline.delay(
                id=str(p.id),
                name=serial["name"],
                parameters=serial["parameters"],
                data_catalog=serial["data_catalog"],
                runner=runner,
                slices=pipeline_input_dict.get("slices", None),
                only_missing=pipeline_input_dict.get("only_missing", False)
            )

            logger.info(
                f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=run_pipeline, id={p.id}, name={p.name}, state=READY, task_id={result.task_id}")

        # If PipelineInput is STAGED and pipeline is not already running or staged
        elif pipeline_input_dict.get("state", None) == "STAGED" and p.status[-1].state.value not in UNREADY_STATES.union(["READY"]) and p.status[-1].state.value != "STAGED":
            p.status.append(PipelineStatus(state=State.STAGED,
                                           runner=runner,
                                           session=None,
                                           started_at=None,
                                           finished_at=None,
                                           task_id=None,
                                           task_name=None))
            logger.info(f'Staging pipeline {p.name}')
        if unique_paths:
            p = generate_unique_paths(p, unique_paths)
        p = info.context["request"].app.backend.update(p)
        logger.info(
            f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=update_pipeline, id={p.id}, name={p.name}")

        return p

    @strawberry.mutation(description="Delete a pipeline.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="delete_pipeline")]), PipelineExtension()])
    def delete_pipeline(self, id: str, info: Info) -> Optional[Pipeline]:
        try:
            p = info.context["request"].app.backend.read(id=id)
            if p is None:
                raise InvalidPipeline(
                    f"Pipeline {id} does not exist in the project.")
        except Exception as e:
            raise InvalidPipeline(f"Error retrieving pipeline {id}: {e}")

        info.context["request"].app.backend.delete(id=id)
        logger.info(f'Deleted {p.name} pipeline with id: ' + str(id))
        return p

    @strawberry.mutation(description="Create a dataset with a signed URL", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="create_dataset")])])
    def create_datasets(self, id: str, info: Info, datasets: List[DataSetInput], expires_in_sec: int = CONFIG["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"]) -> List[JSON | None]:
        """
        Get a signed URL for uploading a dataset.

        Args:
            id (str): The ID of the pipeline.
            info (Info): The GraphQL execution context.
            datasets (List[DataSetInput]): List of datasets for which to create signed URLs. In order to create specific partitions of a PartitionedDataset, pass a DataSetInput with the dataset name and list of partitions e.g. DataSetInput(name="dataset_name", partitions=["partition1", "partition2"]).
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            List[JSON | None]: A signed URL for uploading the dataset or None if not applicable.

        Raises:
            ValueError: If expires_in_sec is greater than max expires_in_sec
            DataSetConfigError: If the dataset configuration is invalid or cannot be parsed.
            TypeError: If the signed URL provider does not inherit from SignedUrlProvider.
        """
        if expires_in_sec > CONFIG["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"]:
            raise ValueError(
                f"expires_in_sec cannot be greater than {CONFIG['KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC']} seconds ({CONFIG['KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC'] // 3600} hours)")
        urls = []
        p = info.context["request"].app.backend.read(id=id)

        if p.status[-1].state.value != "STAGED":
            raise ValueError(
                f"Pipeline {p.name} with id {id} must be staged before creating datasets.")

        # create dict from pipeline data catalog
        catalog = {d.name: d for d in p.data_catalog}
        for dataset_input in datasets:
            dataset = catalog.get(dataset_input.name, None)
            if dataset is None:
                logger.warning(
                    f"Dataset '{dataset_input.name}' not found in the data catalog of pipeline_name={p.name} pipeline_id={p.id}. SignedURL set to None.")
                urls.append({"name": dataset_input.name, "filepath": None,
                            "url": None, "fields": {}})
                continue
            else:
                module_path, class_name = CONFIG["KEDRO_GRAPHQL_SIGNED_URL_PROVIDER"].rsplit(
                    ".", 1)
                module = import_module(module_path)
                cls = getattr(module, class_name)

                if not issubclass(cls, SignedUrlProvider):
                    raise TypeError(
                        f"{class_name} must inherit from SignedUrlProvider")
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=create_dataset, expires_in_sec={expires_in_sec}")
                url = cls.create(info, dataset, expires_in_sec,
                                 dataset_input.partitions)
                urls.append(url)
        return urls


@strawberry.type
class Subscription:
    @strawberry.subscription(description="Subscribe to pipeline events.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="subscribe_to_events")])])
    async def pipeline(self, id: str, info: Info, interval: float = 0.5) -> AsyncGenerator[PipelineEvent]:
        """Subscribe to pipeline events.
        """
        try:
            p = info.context["request"].app.backend.read(id=id)
            if p is None:
                raise InvalidPipeline(
                    f"Pipeline {id} does not exist in the project.")
        except Exception as e:
            raise InvalidPipeline(f"Error retrieving pipeline {id}: {e}")

        while (not p.status[-1].task_id):
            # Wait for the task to be assigned a task_id
            await asyncio.sleep(0.1)
            p = info.context["request"].app.backend.read(id=id)

        if p and p.status[-1].state.value not in READY_STATES:
            async for e in PipelineEventMonitor(app=info.context["request"].app.celery_app, task_id=p.status[-1].task_id).start(interval=interval):
                e["id"] = id
                yield PipelineEvent(**e)
        else:
            yield PipelineEvent(
                id=id,
                task_id=p.status[-1].task_id,
                timestamp=p.status[-1].finished_at,
                status=p.status[-1].state.value,
                result=p.status[-1].task_result,
                traceback=p.status[-1].task_traceback
            )

    @strawberry.subscription(description="Subscribe to pipeline logs.", extensions=[PermissionExtension(permissions=[PERMISSIONS_CLASS(action="subscribe_to_logs")])])
    async def pipeline_logs(self, id: str, info: Info) -> AsyncGenerator[PipelineLogMessage, None]:
        """Subscribe to pipeline logs."""
        try:
            p = info.context["request"].app.backend.read(id=id)
            if p is None:
                raise InvalidPipeline(
                    f"Pipeline {id} does not exist in the project.")
        except Exception as e:
            raise InvalidPipeline(f"Error retrieving pipeline {id}: {e}")

        while (not p.status[-1].task_id):
            # Wait for the task to be assigned a task_id
            await asyncio.sleep(0.1)
            p = info.context["request"].app.backend.read(id=id)

        if p:
            stream = await PipelineLogStream().create(task_id=p.status[-1].task_id, broker_url=info.context["request"].app.config["KEDRO_GRAPHQL_BROKER"])
            async for e in stream.consume():
                e["id"] = id
                yield PipelineLogMessage(**e)


def build_schema(
        type_plugins: dict[str, list],
        directives: Iterable[StrawberryDirective] = (),
        types: Iterable[Union[type, StrawberryType]] = (),
        extensions: Iterable[Union[type[SchemaExtension], SchemaExtension]] = (),
        execution_context_class: Optional[type[GraphQLExecutionContext]] = None,
        config: Optional[StrawberryConfig] = None,
        scalar_overrides: Optional[
            dict[object, Union[type, ScalarWrapper, ScalarDefinition]]
        ] = None,
        schema_directives: Iterable[object] = ()


):

    ComboQuery = merge_types("Query", tuple([Query] + type_plugins["query"]))
    ComboMutation = merge_types("Mutation", tuple(
        [Mutation] + type_plugins["mutation"]))
    ComboSubscription = merge_types("Subscription", tuple(
        [Subscription] + type_plugins["subscription"]))

    return strawberry.Schema(query=ComboQuery,
                             mutation=ComboMutation,
                             subscription=ComboSubscription,
                             directives=directives,
                             types=types,
                             extensions=extensions,
                             execution_context_class=execution_context_class,
                             config=config,
                             scalar_overrides=scalar_overrides,
                             schema_directives=schema_directives)
