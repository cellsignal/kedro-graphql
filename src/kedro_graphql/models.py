import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias

import strawberry
from bson.objectid import ObjectId
from cloudevents.conversion import to_json
from cloudevents.pydantic.v1 import CloudEvent
from fastapi.encoders import jsonable_encoder
from kedro.io import AbstractDataset
from kedro.io.core import _parse_filepath
from kedro.pipeline import Pipeline as KedroPipeline
from strawberry.utils.str_converters import to_camel_case, to_snake_case

from kedro_graphql.exceptions import DataSetConfigError

from .pipeline_config import normalize_pipeline_config

Primitive: TypeAlias = str | bool | int | float
JsonObject: TypeAlias = dict[str, Any]


@strawberry.type
class Tag:
    key: str
    value: str


@strawberry.input
class TagInput:
    key: str
    value: str


@strawberry.enum
class ParameterType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"


def _parameter_type(value: Primitive) -> ParameterType:
    types = {
        str: ParameterType.STRING,
        bool: ParameterType.BOOLEAN,
        int: ParameterType.INTEGER,
        float: ParameterType.FLOAT,
    }
    try:
        return types[type(value)]
    except KeyError as exc:
        raise ValueError(
            f"Only str, bool, int, and float parameters are supported; got {type(value).__name__}"
        ) from exc


def _parameter_type_from_wire(value: str | ParameterType | None) -> ParameterType:
    if value is None:
        return ParameterType.STRING
    if isinstance(value, ParameterType):
        return value
    try:
        return ParameterType[value.upper()]
    except KeyError as exc:
        raise ValueError(f"Unknown parameter type: {value}") from exc


@strawberry.type
class Parameter:
    name: str
    value: str
    type: ParameterType = ParameterType.STRING

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Parameter":
        return cls(
            name=str(payload["name"]),
            value=str(payload["value"]),
            type=_parameter_type_from_wire(payload.get("type")),
        )

    @classmethod
    def from_value(cls, name: str, value: Primitive) -> "Parameter":
        return cls(name=name, value=str(value), type=_parameter_type(value))

    def serialize(self) -> dict[str, Primitive]:
        value: Primitive = self.value
        if self.type is ParameterType.BOOLEAN:
            normalized = self.value.lower()
            if normalized not in {"true", "false"}:
                raise ValueError("Boolean parameters must be 'true' or 'false'")
            value = normalized == "true"
        elif self.type is ParameterType.INTEGER:
            value = int(self.value)
        elif self.type is ParameterType.FLOAT:
            value = float(self.value)
        return {self.name: value}


@strawberry.input
class ParameterInput:
    name: str
    value: str
    type: ParameterType = ParameterType.STRING

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ParameterInput":
        return cls(
            name=str(payload["name"]),
            value=str(payload["value"]),
            type=_parameter_type_from_wire(payload.get("type")),
        )


def parameter_inputs_from_mapping(
    parameters: Mapping[str, Primitive],
) -> list[ParameterInput]:
    return [
        ParameterInput(name=name, value=str(value), type=_parameter_type(value))
        for name, value in parameters.items()
    ]


@strawberry.type
class DataSet:
    name: str
    config: str
    tags: list[Tag] = strawberry.field(default_factory=list)

    @strawberry.field
    def exists(self) -> bool:
        return AbstractDataset.from_config(self.name, self.parse_config()).exists()

    @strawberry.field
    def partitions(self) -> list[str]:
        config = self.parse_config()
        if "type" not in config:
            raise DataSetConfigError(
                "Invalid dataset configuration. Must have 'type' key"
            )
        if config["type"] != "partitions.PartitionedDataset":
            raise DataSetConfigError(
                "Dataset is not a PartitionedDataset. 'partitions' is only available for PartitionedDatasets."
            )
        partitions = AbstractDataset.from_config(self.name, config).load()
        return list(partitions)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DataSet":
        config = payload.get("config")
        if not isinstance(config, str):
            raise DataSetConfigError("Dataset config must be a JSON string")
        return cls(
            name=str(payload["name"]),
            config=config,
            tags=[Tag(**tag) for tag in payload.get("tags") or []],
        )

    def serialize(self) -> dict[str, JsonObject]:
        return {self.name: self.parse_config()}

    def parse_config(self) -> JsonObject:
        try:
            value = json.loads(self.config)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DataSetConfigError(
                f"Unable to parse dataset config as JSON: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise DataSetConfigError("Dataset config must be a JSON object")
        return value

    def parse_filepath(self) -> tuple[str, str]:
        filepath = self.parse_config().get("filepath")
        if not isinstance(filepath, str) or not filepath:
            raise DataSetConfigError(
                "Invalid dataset configuration. Must have 'filepath' key"
            )
        return _parse_filepath(filepath)["protocol"], filepath

    def parse_path(self) -> tuple[str, str]:
        path = self.parse_config().get("path")
        if not isinstance(path, str) or not path:
            raise DataSetConfigError(
                "Invalid dataset configuration. Must have 'path' key"
            )
        return _parse_filepath(path)["protocol"], path


@strawberry.input
class DataSetInput:
    name: str
    config: str | None = None
    tags: list[TagInput] = strawberry.field(default_factory=list)
    partitions: list[str] = strawberry.field(default_factory=list)
    list_partitions: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DataSetInput":
        values = _snake_case_keys(payload)
        return cls(
            name=str(values["name"]),
            config=values.get("config"),
            tags=[TagInput(**tag) for tag in values.get("tags") or []],
            partitions=list(values.get("partitions") or []),
            list_partitions=bool(values.get("list_partitions", False)),
        )

    def to_graphql(self) -> JsonObject:
        return {
            to_camel_case(key): value for key, value in jsonable_encoder(self).items()
        }


def dataset_inputs_from_mapping(
    catalog: Mapping[str, Mapping[str, Any]],
) -> list[DataSetInput]:
    return [
        DataSetInput(name=name, config=json.dumps(config))
        for name, config in catalog.items()
    ]


@dataclass
class DataSetPartitions:
    name: str
    partitions: list[str]
    config: str | None = None
    tags: list[Tag] = field(default_factory=list)

    @classmethod
    def from_graphql(cls, payload: Mapping[str, Any]) -> "DataSetPartitions":
        result = _snake_case_keys(payload)
        return cls(
            name=result["name"],
            config=result.get("config"),
            tags=[Tag(**tag) for tag in result.get("tags") or []],
            partitions=result.get("partitions") or [],
        )


@strawberry.type
class Node:
    name: str
    inputs: list[str]
    outputs: list[str]
    tags: list[str]


@strawberry.type(
    description="PipelineTemplates are definitions of Pipelines. They represent the supported interface for executing a Pipeline."
)
class PipelineTemplate:
    id: str = strawberry.field(description="ID of the pipeline template.")
    name: str
    kedro_pipelines: strawberry.Private[Mapping[str, KedroPipeline]]
    kedro_catalog: strawberry.Private[Mapping[str, JsonObject]]
    kedro_parameters: strawberry.Private[Mapping[str, Any]]

    def _resolved_config(
        self,
    ) -> tuple[dict[str, JsonObject], dict[str, Primitive], dict[str, str]]:
        return normalize_pipeline_config(
            self.kedro_pipelines[self.name], self.kedro_catalog, self.kedro_parameters
        )

    @strawberry.field
    def describe(self) -> str:
        return self.kedro_pipelines[self.name].describe()

    @strawberry.field
    def nodes(self) -> list[Node]:
        return [
            Node(
                name=node.name, inputs=node.inputs, outputs=node.outputs, tags=node.tags
            )
            for node in self.kedro_pipelines[self.name].nodes
        ]

    @strawberry.field
    def parameters(self) -> list[Parameter]:
        _, parameters, _ = self._resolved_config()
        return [Parameter.from_value(name, value) for name, value in parameters.items()]

    @strawberry.field
    def inputs(self) -> list[DataSet]:
        catalog, _, _ = self._resolved_config()
        return [
            DataSet(name=name, config=json.dumps(catalog[name]))
            for name in sorted(self.kedro_pipelines[self.name].all_inputs())
            if name in catalog
        ]

    @strawberry.field
    def outputs(self) -> list[DataSet]:
        catalog, _, _ = self._resolved_config()
        return [
            DataSet(name=name, config=json.dumps(catalog[name]))
            for name in sorted(self.kedro_pipelines[self.name].all_outputs())
            if name in catalog
        ]


@strawberry.type
class PageMeta:
    next_cursor: str | None = strawberry.field(
        default=None, description="The next cursor to continue with."
    )


@strawberry.type
class PipelineTemplates:
    pipeline_templates: list[PipelineTemplate] = strawberry.field(
        description="The list of pipeline templates."
    )
    page_meta: PageMeta = strawberry.field(description="Metadata to aid in pagination.")

    @staticmethod
    def _build_pipeline_index(
        kedro_pipelines: Mapping[str, KedroPipeline],
        kedro_catalog: Mapping[str, JsonObject],
        kedro_parameters: Mapping[str, Any],
    ) -> list[PipelineTemplate]:
        count = 100000000000000000000000
        return [
            PipelineTemplate(
                name=name,
                id=str(ObjectId(str(count + index))),
                kedro_pipelines=kedro_pipelines,
                kedro_catalog=kedro_catalog,
                kedro_parameters=kedro_parameters,
            )
            for index, name in enumerate(kedro_pipelines)
        ]


@strawberry.enum
class PipelineSliceType(Enum):
    TAGS = "tags"
    FROM_NODES = "from_nodes"
    TO_NODES = "to_nodes"
    NODE_NAMES = "node_names"
    FROM_INPUTS = "from_inputs"
    TO_OUTPUTS = "to_outputs"
    NODE_NAMESPACE = "node_namespace"


@strawberry.input(description="Slice a pipeline.")
class PipelineSlice:
    slice: PipelineSliceType
    args: list[str]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PipelineSlice":
        slice_type = payload["slice"]
        if not isinstance(slice_type, PipelineSliceType):
            slice_type = PipelineSliceType[str(slice_type).upper()]
        return cls(slice=slice_type, args=list(payload["args"]))


@strawberry.enum
class PipelineInputStatus(Enum):
    STAGED = "STAGED"
    READY = "READY"
    ABORTED = "ABORTED"


@strawberry.input(description="PipelineInput")
class PipelineInput:
    name: str
    state: PipelineInputStatus = PipelineInputStatus.STAGED
    parameters: list[ParameterInput] = strawberry.field(default_factory=list)
    data_catalog: list[DataSetInput] = strawberry.field(default_factory=list)
    tags: list[TagInput] = strawberry.field(default_factory=list)
    parent: strawberry.ID | None = None
    runner: str | None = None
    slices: list[PipelineSlice] = strawberry.field(default_factory=list)
    only_missing: bool = False
    hooks: list[str] = strawberry.field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PipelineInput":
        values = _snake_case_keys(payload)
        state = values.get("state", PipelineInputStatus.STAGED)
        if not isinstance(state, PipelineInputStatus):
            state = PipelineInputStatus[str(state).upper()]
        return cls(
            name=str(values["name"]),
            state=state,
            parameters=[
                ParameterInput.from_dict(item)
                for item in values.get("parameters") or []
            ],
            data_catalog=[
                DataSetInput.from_dict(item)
                for item in values.get("data_catalog") or []
            ],
            tags=[TagInput(**item) for item in values.get("tags") or []],
            parent=values.get("parent"),
            runner=values.get("runner"),
            slices=[
                PipelineSlice.from_dict(item) for item in values.get("slices") or []
            ],
            only_missing=bool(values.get("only_missing", False)),
            hooks=list(values.get("hooks") or []),
        )

    @classmethod
    def create(
        cls,
        name: str,
        data_catalog: Mapping[str, Mapping[str, Any]] | None = None,
        parameters: Mapping[str, Primitive] | None = None,
        tags: Mapping[str, str] | None = None,
        hooks: list[str] | None = None,
    ) -> "PipelineInput":
        return cls(
            name=name,
            parameters=parameter_inputs_from_mapping(parameters or {}),
            data_catalog=dataset_inputs_from_mapping(data_catalog or {}),
            tags=[
                TagInput(key=key, value=value) for key, value in (tags or {}).items()
            ],
            hooks=list(hooks or []),
        )

    def to_graphql(self) -> JsonObject:
        payload = jsonable_encoder(self)
        payload["data_catalog"] = [
            dataset.to_graphql() for dataset in self.data_catalog
        ]
        for parameter in payload["parameters"]:
            parameter["type"] = parameter["type"].upper()
        return {to_camel_case(key): value for key, value in payload.items()}

    @classmethod
    def from_event(
        cls, name: str, state: PipelineInputStatus, event: CloudEvent
    ) -> "PipelineInput":
        event_bytes = to_json(event)
        event_data = json.loads(event_bytes.decode())
        event_id = event_data.get("id")
        source = event_data.get("source")
        event_type = event_data.get("type")
        if not event_id or not source or not event_type:
            raise ValueError(
                "CloudEvent must have 'id', 'source', and 'type' attributes"
            )
        return cls(
            name=name,
            state=state,
            parameters=[
                ParameterInput(
                    name="event",
                    value=event_bytes.decode(),
                    type=ParameterType.STRING,
                )
            ],
            tags=[
                TagInput(key="event_id", value=event_id),
                TagInput(key="event_source", value=source),
                TagInput(key="event_type", value=event_type),
            ],
        )


@strawberry.enum
class State(Enum):
    READY = "READY"
    STAGED = "STAGED"
    STARTED = "STARTED"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"
    RETRY = "RETRY"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    REVOKED = "REVOKED"
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"


@strawberry.type
class PipelineStatus:
    state: State
    session: str | None = None
    runner: str | None = None
    filtered_nodes: list[str] = strawberry.field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    abort_requested_at: datetime | None = None
    abort_completed_at: datetime | None = None
    task_id: str | None = None
    task_name: str | None = None
    task_args: str | None = None
    task_kwargs: str | None = None
    task_request: str | None = None
    task_exception: str | None = None
    task_traceback: str | None = None
    task_einfo: str | None = None
    task_result: str | None = None


def _snake_case_keys(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            to_snake_case(str(key)): _snake_case_keys(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_snake_case_keys(item) for item in value]
    return value


def _decode_datetime(value: str | datetime | None) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def _decode_status(payload: Mapping[str, Any]) -> PipelineStatus:
    values = _snake_case_keys(payload)
    return PipelineStatus(
        **{
            **{
                key: value
                for key, value in values.items()
                if key in PipelineStatus.__dataclass_fields__
            },
            "state": State(values["state"]),
            "filtered_nodes": values.get("filtered_nodes") or [],
            "started_at": _decode_datetime(values.get("started_at")),
            "finished_at": _decode_datetime(values.get("finished_at")),
            "abort_requested_at": _decode_datetime(values.get("abort_requested_at")),
            "abort_completed_at": _decode_datetime(values.get("abort_completed_at")),
        }
    )


@strawberry.type
class Pipeline:
    id: strawberry.ID | None = None
    name: str
    data_catalog: list[DataSet] = strawberry.field(default_factory=list)
    describe: str | None = None
    nodes: list[Node] = strawberry.field(default_factory=list)
    parameters: list[Parameter] = strawberry.field(default_factory=list)
    status: list[PipelineStatus] = strawberry.field(default_factory=list)
    tags: list[Tag] = strawberry.field(default_factory=list)
    created_at: datetime | None = None
    parent: strawberry.ID | None = None
    project_version: str | None = None
    pipeline_version: str | None = None
    kedro_graphql_version: str | None = None
    hooks: list[str] = strawberry.field(default_factory=list)

    def to_kedro(self) -> JsonObject:
        parameters: dict[str, Primitive] = {}
        for parameter in self.parameters:
            parameters.update(parameter.serialize())
        catalog: dict[str, JsonObject] = {}
        for dataset in self.data_catalog:
            catalog.update(dataset.serialize())
        return {
            "id": str(self.id),
            "name": self.name,
            "data_catalog": catalog,
            "parameters": parameters,
            "hooks": self.hooks,
        }

    def to_dict(self) -> JsonObject:
        return jsonable_encoder(self, custom_encoder={ObjectId: str})

    def to_input(self) -> PipelineInput:
        return PipelineInput(
            name=self.name,
            data_catalog=[
                DataSetInput(name=dataset.name, config=dataset.config)
                for dataset in self.data_catalog
            ],
            parameters=[
                ParameterInput(
                    name=parameter.name,
                    value=parameter.value,
                    type=parameter.type,
                )
                for parameter in self.parameters
            ],
            tags=[TagInput(key=tag.key, value=tag.value) for tag in self.tags],
            hooks=list(self.hooks),
        )

    @classmethod
    def from_input(cls, pipeline_input: PipelineInput) -> "Pipeline":
        return cls.from_dict(jsonable_encoder(pipeline_input))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Pipeline":
        values = _snake_case_keys(payload)
        converters = {
            "created_at": _decode_datetime,
            "data_catalog": lambda items: [
                DataSet.from_dict(item) for item in items or []
            ],
            "nodes": lambda items: [
                Node(
                    **{
                        key: value
                        for key, value in item.items()
                        if key in Node.__dataclass_fields__
                    }
                )
                for item in items or []
            ],
            "parameters": lambda items: [
                Parameter.from_dict(item) for item in items or []
            ],
            "status": lambda items: [_decode_status(item) for item in items or []],
            "tags": lambda items: [Tag(**item) for item in items or []],
            "hooks": lambda items: list(items or []),
        }
        converted = {
            key: converters[key](value) if key in converters else value
            for key, value in values.items()
            if key in cls.__dataclass_fields__
        }
        for field_name in (
            "data_catalog",
            "nodes",
            "parameters",
            "status",
            "tags",
            "hooks",
        ):
            converted.setdefault(field_name, [])
        return cls(**converted)


@strawberry.type
class Pipelines:
    pipelines: list[Pipeline] = strawberry.field(
        description="The list of pipeline instances."
    )
    page_meta: PageMeta = strawberry.field(description="Metadata to aid in pagination.")

    @classmethod
    def from_graphql(cls, payload: Mapping[str, Any]) -> "Pipelines":
        result = _snake_case_keys(payload)["read_pipelines"]
        return cls(
            page_meta=PageMeta(**result["page_meta"]),
            pipelines=[Pipeline.from_dict(item) for item in result["pipelines"]],
        )


@strawberry.type
class PipelineEvent:
    id: str
    task_id: str
    status: str
    result: str | None
    timestamp: str
    traceback: str | None

    @classmethod
    def from_graphql(cls, payload: Mapping[str, Any]) -> "PipelineEvent":
        return cls(**_snake_case_keys(payload["pipeline"]))


@strawberry.type
class PipelineLogMessage:
    id: str
    message: str
    message_id: str
    task_id: str
    time: str

    @classmethod
    def from_graphql(cls, payload: Mapping[str, Any]) -> "PipelineLogMessage":
        result = _snake_case_keys(payload["pipelineLogs"])
        return cls(
            id=result["id"],
            message=result.get("message", ""),
            message_id=result.get("message_id", ""),
            task_id=result.get("task_id", ""),
            time=result.get("time", ""),
        )


@strawberry.type
class SignedUrlField:
    name: str
    value: str


@strawberry.type
class SignedUrl:
    url: str
    file: str
    fields: list[SignedUrlField] = strawberry.field(default_factory=list)

    @classmethod
    def from_graphql(cls, payload: Mapping[str, Any]) -> "SignedUrl":
        result = _snake_case_keys(payload)
        return cls(
            url=result["url"],
            file=result["file"],
            fields=[SignedUrlField(**field) for field in result.get("fields") or []],
        )

    def get_field_value(self, name: str) -> str | None:
        return next((field.value for field in self.fields if field.name == name), None)


@strawberry.type
class SignedUrls:
    urls: list[SignedUrl]

    @classmethod
    def from_graphql(cls, payload: Mapping[str, Any]) -> "SignedUrls":
        result = _snake_case_keys(payload)
        return cls(urls=[SignedUrl.from_graphql(item) for item in result["urls"]])
