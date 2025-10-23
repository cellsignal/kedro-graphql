import json
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
# from kedro.io.core import _parse_filepath
# from .signed_url.local_file_provider import LocalFileProvider
# from .signed_url.base import PreSignedUrlProvider
# from importlib import import_module
import strawberry
from bson.objectid import ObjectId
from fastapi.encoders import jsonable_encoder
from kedro.io import AbstractDataset
from kedro.io.core import _parse_filepath
from strawberry.utils.str_converters import to_camel_case, to_snake_case
from cloudevents.conversion import to_json
from cloudevents.pydantic.v1 import CloudEvent
from pathlib import Path

from kedro_graphql.exceptions import DataSetConfigError
# from strawberry.permission import PermissionExtension

from .config import load_config
from .logs.logger import logger
# from .permissions import get_permissions


CONFIG = load_config()
# logger.debug("configuration loaded by {s}".format(s=__name__))
##
# PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))
# logger.info("{s} using permissions class: {d}".format(s=__name__, d=PERMISSIONS_CLASS))


def mark_deprecated(default=None):
    return strawberry.field(default=default, deprecation_reason="see " + str(CONFIG["KEDRO_GRAPHQL_DEPRECATIONS_DOCS"]))


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


@strawberry.type
class Parameter:
    name: str
    value: str
    type: Optional[ParameterType] = ParameterType.STRING

    @staticmethod
    def decode(input_dict) -> dict:
        """
        Returns a Parameter object from a dictionary.
        """
        if input_dict.get("type", False):
            return Parameter(
                name=input_dict["name"],
                value=input_dict["value"],
                type=ParameterType[input_dict["type"].upper()])
        else:
            return Parameter(**input_dict)

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        value = self.value
        if self.type == "boolean":
            value = self.value.lower()
            if value == "true":
                value = True
            elif value == "false":
                value = False
            else:
                raise ValueError(
                    "Parameter of type BOOL must be one of 'True', 'true', 'False', or 'false'")

        elif self.type == "integer":
            value = int(self.value)

        elif self.type == "float":
            value = float(self.value)

        return {self.name: value}


@strawberry.input
class ParameterInput:
    name: str
    value: str
    type: Optional[ParameterType] = ParameterType.STRING

    @staticmethod
    def create(parameters: dict):

        def _create_parameter_input(name, value):

            type_map = [
                (int, ParameterType.INTEGER),
                (float, ParameterType.FLOAT),
                (bool, ParameterType.BOOLEAN),
                (str, ParameterType.STRING),
            ]

            try:
                type_enum: ParameterType = next(
                    t[1] for t in type_map if type(value) == t[0])
            except StopIteration:
                raise ValueError(
                    f"Only primitive types are supported ({' '.join(str(x[0]) for x in type_map)}). Got {type(value)}"
                )

            return ParameterInput(name=name, value=str(value), type=type_enum.value.upper())

        params = [_create_parameter_input(k, v) for k, v in parameters.items()]
        return params


@strawberry.input
class CredentialSetInput:
    name: str
    value: str

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        return {self.name: self.value}


@strawberry.input
class CredentialInput:
    name: str
    value: List[CredentialSetInput]

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        values = {}
        for v in self.value:
            values.update(v.serialize())
        return {self.name: values}


@strawberry.input
class CredentialNestedInput:
    name: str
    value: List[CredentialInput]

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        values = {}
        for v in self.value:
            values.update(v.serialize())
        return {self.name: values}


@strawberry.type
class DataSet:
    name: str
    config: Optional[str] = None
    # credentials: Optional[List[CredentialInput]]
    tags: Optional[List[Tag]] = None

    @strawberry.field
    def exists(self) -> bool:
        if self.config:
            return AbstractDataset.from_config(self.name, self.parse_config()).exists()
        else:
            return False

    @strawberry.field
    def partitions(self) -> Optional[List[str]]:
        config = self.parse_config()
        if not config.get("type", None):
            raise DataSetConfigError(
                "Invalid dataset configuration. Must have 'type' key")
        elif config["type"] != "partitions.PartitionedDataset":
            raise DataSetConfigError(
                "Dataset is not a PartitionedDataset. 'partitions' field is only available for PartitionedDatasets."
            )
        else:
            partitions = AbstractDataset.from_config(self.name, config).load()
            return list(partitions.keys())

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        temp = self.__dict__.copy()
        temp.pop("name")
        return {self.name: json.loads(temp['config'])}

    @staticmethod
    def decode(payload):
        """
        Return a new DataSet from a dictionary.

        Args:
            payload (dict): dict representing DataSet e.g.

                {
                  "name": "text_in",
                  "config": '{"filepath": "./data/01_raw/text_in.txt", "type": "text.TextDataSet", "save_args": [{"name": "say", "value": "hello"}], "load_args": [{"name": "say", "value": "hello"}]}',
                  "tags":[{"key": "owner name", "value": "harinlee0803"},{"key": "owner email", "value": "test@example.com"}]
                }

        """
        if payload.get("tags", False):
            tags = [Tag(**t) for t in payload["tags"]]
        else:
            tags = None

        return DataSet(
            name=payload["name"],
            config=payload["config"],
            tags=tags
        )

    def parse_config(self) -> dict:
        """
        Return the config as a dictionary.

        Example usage:

            from kedro_graphql.models import DataSet

            d = DataSet(name="text_in", config='{"filepath": "./data/01_raw/text_in.txt", "type": "text.TextDataSet", "save_args": [{"name": "say", "value": "hello"}], "load_args": [{"name": "say", "value": "hello"}]}')

            print(d.parse_config())

            {'filepath': './data/01_raw/text_in.txt',
             'type': 'text.TextDataSet',
             'save_args': [{'name': 'say', 'value': 'hello'}],
             'load_args': [{'name': 'say', 'value': 'hello'}]}

        """
        try:
            return json.loads(self.config)
        except json.JSONDecodeError as e:
            raise DataSetConfigError(f"Unable to parse JSON in config: {e}")
        except Exception as e:
            raise DataSetConfigError(f"Invalid dataset configuration: {e}")

    def parse_filepath(self) -> tuple[str, str]:
        """
        Parse the filepath from the dataset configuration.

        Args:
            config (dict): The dataset configuration.

        Returns:
            tuple[str, str]: (protocol, the file path).
        """
        config = self.parse_config()
        filepath = config.get("filepath", None)
        if not filepath:
            raise DataSetConfigError(
                "Invalid dataset configuration. Must have 'filepath' key")

        return _parse_filepath(filepath)["protocol"], filepath

    def parse_path(self) -> tuple[str, str]:
        """
        Parse the path from the dataset configuration.

        Args:
            config (dict): The dataset configuration.

        Returns:
            tuple[str, str]: (protocol, the file path).
        """
        path = self.parse_config().get("path", None)
        if not path:
            raise DataSetConfigError(
                "Invalid dataset configuration. Must have 'path' key")

        return _parse_filepath(path)["protocol"], path


@strawberry.input
class DataSetInput:
    name: str
    config: Optional[str] = None
    tags: Optional[List[TagInput]] = None
    partitions: Optional[List[str]] = None

    def encode(self, encoder="graphql"):
        if encoder == "dict":
            return jsonable_encoder(self)
        elif encoder == "graphql":
            p = jsonable_encoder(self)
            p = {to_camel_case(k): v for k, v in p.items()}
            return p
        else:
            raise TypeError("encoder must be 'dict' or 'graphql'")


class DataCatalog:
    datasets: List[DataSet]


@strawberry.input
class DataCatalogInput:
    datasets: List[DataSetInput]

    @staticmethod
    def create(config):
        """
        context.config_loader["catalog"]

        {'text_in': {'type': 'text.TextDataSet',
                     'filepath': './data/01_raw/text_in.txt'},
         'text_out': {'type': 'text.TextDataSet',
                      'filepath': './data/02_intermediate/text_out.txt'}}

        Example usage:

            from kedro_graphql.models import DataCatalogInput

            catalog = DataCatalogInput.create(context.config_loader["catalog"])

            print(catalog)

            [DataSetInput(name='text_in', config='{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}', type=None, filepath=None, save_args=None, load_args=None, credentials=None),
             DataSetInput(name='text_out', config='{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}', type=None, filepath=None, save_args=None, load_args=None, credentials=None)]

        """
        return [DataSetInput(name=k, config=json.dumps(v)) for k, v in config.items()]


@strawberry.type
class Node:
    name: str
    inputs: List[str]
    outputs: List[str]
    tags: List[str]


@strawberry.type(description="PipelineTemplates are definitions of Pipelines.  They represent the supported interface for executing a Pipeline.")
class PipelineTemplate:
    id: str = strawberry.field(description="ID of the pipeline template.")
    name: str
    kedro_pipelines: strawberry.Private[dict]
    kedro_catalog: strawberry.Private[dict]
    kedro_parameters: strawberry.Private[dict]

    @strawberry.field
    def describe(self) -> str:
        return self.kedro_pipelines[self.name].describe()

    @strawberry.field
    def nodes(self) -> List[Node]:
        nodes = self.kedro_pipelines[self.name].nodes

        return [Node(name=n.name, inputs=n.inputs, outputs=n.outputs, tags=n.tags) for n in nodes]

    @strawberry.field
    def parameters(self) -> List[Parameter]:
        # keep track of parameters to avoid returning duplicates
        params = {}
        for n in self.kedro_pipelines[self.name].all_inputs():
            if n.startswith("params:"):
                name = n.split("params:")[1]
                value = self.kedro_parameters[name]
                if not params.get(name, False):
                    params[name] = value
            elif n == "parameters":
                for k, v in self.kedro_parameters.items():
                    if not params.get(k, False):
                        params[k] = v
        return [Parameter(name=k, value=v) for k, v in params.items()]

    @strawberry.field
    def inputs(self) -> List[DataSet]:
        inputs_resolved = []
        for n in self.kedro_pipelines[self.name].all_inputs():
            if not n.startswith("params:") and n != "parameters":
                config = self.kedro_catalog[n]
                inputs_resolved.append(DataSet(name=n, config=json.dumps(config)))

        return inputs_resolved

    @strawberry.field
    def outputs(self) -> List[DataSet]:
        outputs_resolved = []
        for n in self.kedro_pipelines[self.name].all_outputs():
            if self.kedro_catalog.get(n, None):
                config = self.kedro_catalog[n]
                outputs_resolved.append(DataSet(name=n, config=json.dumps(config)))
            else:
                logger.warning(
                    f"PipelineTemplate '{self.name}' has an output '{n}' that is not defined in the catalog. This may be due to a missing dataset configuration or because it is a MemoryDataset."
                )

        return outputs_resolved


@strawberry.type
class PageMeta:
    next_cursor: Optional[str] = strawberry.field(
        description="The next cursor to continue with."
    )


@strawberry.type
class PipelineTemplates:
    pipeline_templates: List[PipelineTemplate] = strawberry.field(
        description="The list of pipeline templates.")

    page_meta: PageMeta = strawberry.field(description="Metadata to aid in pagination.")

    @staticmethod
    def _build_pipeline_index(kedro_pipelines, kedro_catalog, kedro_parameters):
        """
        """
        pipes = []
        count = 100000000000000000000000
        for k, v in kedro_pipelines.items():
            pipes.append(PipelineTemplate(name=k,
                                          id=ObjectId(str(count)),
                                          kedro_pipelines=kedro_pipelines,
                                          kedro_catalog=kedro_catalog,
                                          kedro_parameters=kedro_parameters))
            count += 1

        return pipes


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
    args: List[str]  # e.g. ["node1", "node2"]


@strawberry.enum
class PipelineInputStatus(Enum):
    STAGED = "STAGED"
    READY = "READY"


@strawberry.input(description="PipelineInput")
class PipelineInput:
    name: str
    state: PipelineInputStatus = PipelineInputStatus.STAGED
    parameters: Optional[List[ParameterInput]] = None
    data_catalog: Optional[List[DataSetInput]] = None
    tags: Optional[List[TagInput]] = None
    parent: Optional[strawberry.ID] = None
    runner: Optional[str] = None
    slices: Optional[List[PipelineSlice]] = None
    only_missing: Optional[bool] = False

    @staticmethod
    def create(name=None, data_catalog=None, parameters=None, tags=None):
        """
        Example usage:

            from kedro_graphql.models import PipelineInput
            from fastapi.encoders import jsonable_encoder

            p = PipelineInput(name = "example00",
                         data_catalog = context.config_loader["catalog"],
                         parameters = context.config_loader["parameters"],
                         tags = [{""owner":"person"}])

            print(p)

            PipelineInput(name='example00',
                          parameters=[
                            ParameterInput(name='example',
                                           value='hello',
                                           type=<ParameterType.STRING: 'string'>),
                            ParameterInput(name='duration', value='1', type=<ParameterType.STRING: 'string'>)
                          ],
                          data_catalog=[
                            DataSetInput(
                                name='text_in', config='{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}'),
                            DataSetInput(
                                name='text_out', config='{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}')
                          ],
                          tags=[TagInput(key='owner', value='sean')])

            print(jsonable_encoder(p))

            ## this can be used as the PipelineInput parameter when calleing the pipeline mutation via the API
            {'name': 'example00',
            'parameters': [{'name': 'example', 'value': 'hello', 'type': 'string'},
             {'name': 'duration', 'value': '1', 'type': 'string'}],
            'data_catalog': [{'name': 'text_in',
              'config': '{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}'},
             {'name': 'text_out',
              'config': '{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}'}],
            'tags': [{'key': 'owner', 'value': 'sean'}],
            'credentials': None,
            'credentials_nested': None}

        """
        if tags:
            tags = [TagInput(key=k, value=v) for t in tags for k, v in tags.items()]

        if data_catalog:
            data_catalog = DataCatalogInput.create(data_catalog)

        if parameters:
            parameters = ParameterInput.create(parameters)

        return PipelineInput(name=name,
                             parameters=parameters,
                             data_catalog=data_catalog,
                             tags=tags)

    def encode(self, encoder="graphql"):
        if encoder == "dict":
            return jsonable_encoder(self)
        elif encoder == "graphql":
            p = jsonable_encoder(self)
            p = {to_camel_case(k): v for k, v in p.items()}
            # make sure parameter types are uppercase
            if p.get("parameters", None):
                for param in p["parameters"]:
                    if param.get("type", None):
                        param["type"] = param["type"].upper()
            return p
        else:
            raise TypeError("encoder must be 'dict' or 'graphql'")

    @classmethod
    def from_event(cls, name: str, state: PipelineInputStatus, event: CloudEvent) -> "PipelineInput":
        """
        Factory method to create a new PipelineInput from a CloudEvent. 
        Tags will be added for event metadata and the entire event will be added 
        as a single parameter (json-serialized).
        """
        event_bytes = to_json(event)
        event = json.loads(event_bytes.decode())

        id = event.get("id")
        source = event.get("source")
        type = event.get("type")

        if not id or not source or not type:
            raise ValueError(
                "CloudEvent must have 'id', 'source', and 'type' attributes")

        return cls(
            name=name,
            state=state,
            parameters=[ParameterInput(
                name="event", value=event_bytes, type="STRING")],
            tags=[
                {"key": "event_id", "value": id},
                {"key": "event_source", "value": source},
                {"key": "event_type", "value": type}
            ]
        )


@strawberry.enum
class State(Enum):
    READY = 'READY'
    STAGED = 'STAGED'
    STARTED = 'STARTED'
    RETRY = 'RETRY'
    FAILURE = 'FAILURE'
    SUCCESS = 'SUCCESS'
    REVOKED = 'REVOKED'
    PENDING = 'PENDING'
    RECIEVED = 'RECIEVED'


@strawberry.type
class PipelineStatus:
    state: State
    session: Optional[str]
    runner: Optional[str] = None
    filtered_nodes: Optional[List[str]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    task_args: Optional[str] = None
    task_kwargs: Optional[str] = None
    task_request: Optional[str] = None
    task_exception: Optional[str] = None
    task_traceback: Optional[str] = None
    task_einfo: Optional[str] = None
    task_result: Optional[str] = None


@strawberry.type
class Pipeline:
    id: Optional[strawberry.ID] = None
    name: str
    data_catalog: Optional[List[DataSet]] = None
    describe: Optional[str] = None
    nodes: Optional[List[Node]] = None
    parameters: Optional[List[Parameter]] = None
    status: List[PipelineStatus] = strawberry.field(default_factory=list)
    tags: Optional[List[Tag]] = None
    created_at: Optional[datetime] = None
    parent: Optional[strawberry.ID] = None
    project_version: Optional[str] = None
    pipeline_version: Optional[str] = None
    kedro_graphql_version: Optional[str] = None

    def serialize(self):
        parameters = {}
        data_catalog = {}

        if self.parameters:
            for p in self.parameters:
                s = p.serialize()
                parameters.update(s)

        if self.data_catalog:
            for d in self.data_catalog:
                s = d.serialize()
                data_catalog.update(s)

        return {
            "id": str(self.id),
            "name": self.name,
            "data_catalog": data_catalog,
            "parameters": parameters,
        }

    def encode(self, encoder="dict"):

        if encoder == "dict":
            p = deepcopy(self)
            # if type ObjectID the jsonable_encoder will throw an error
            p.id = str(p.id)
            encoded_pipeline = jsonable_encoder(p)

            return encoded_pipeline
        elif encoder == "kedro":
            return self.serialize()
        elif encoder == "input":
            if self.parameters:
                parameters = [ParameterInput(name=p.name, value=p.value, type=p.type.value)
                              for p in self.parameters]
            else:
                parameters = None
            return PipelineInput(
                name=self.name,
                data_catalog=[DataSetInput(name=d.name, config=d.config)
                              for d in self.data_catalog],
                parameters=parameters,
                tags=[TagInput(key=t.key, value=t.value)
                      for t in self.tags] if self.tags else None
            )
        else:
            raise TypeError("encoder must be 'dict', 'kedro', or 'input'")

    @classmethod
    def decode(cls, payload, decoder=None):
        """Factory method to create a new Pipeline from a dictionary or graphql api response.
        """
        if decoder == "graphql":
            payload = {to_snake_case(k): v for k, v in payload.items()}
            if payload["status"]:
                payload["status"] = [
                    {to_snake_case(k): v for k, v in s.items()} for s in payload["status"]]

            return cls.decode_dict(payload)

        elif decoder == "dict" or isinstance(payload, dict):
            return cls.decode_dict(payload)

        elif isinstance(payload, PipelineInput):
            return cls.decode_pipeline_input(payload)

    @staticmethod
    def decode_dict(payload):
        if payload.get("tags", None):
            tags = [Tag(**t) for t in payload["tags"]]
        else:
            tags = None

        if payload.get("data_catalog", None):
            data_catalog = [DataSet.decode(d) for d in payload["data_catalog"]]
        else:
            data_catalog = []

        if payload.get("status", None):
            status = [PipelineStatus(
                state=State[s["state"]],
                session=s["session"],
                runner=s.get("runner", "kedro.runner.SequentialRunner"),
                filtered_nodes=s.get("filtered_nodes"),
                started_at=datetime.fromisoformat(
                    s["started_at"]) if s.get("started_at") else None,
                finished_at=datetime.fromisoformat(
                    s["finished_at"]) if s.get("finished_at") else None,
                task_name=s.get("task_name"),
                task_id=s.get("task_id"),
                task_args=s.get("task_args"),
                task_kwargs=s.get("task_kwargs"),
                task_request=s.get("task_request"),
                task_exception=s.get("task_exception"),
                task_traceback=s.get("task_traceback"),
                task_einfo=s.get("task_einfo"),
                task_result=s.get("task_result")
            ) for s in payload["status"]]
        else:
            status = []

        if payload.get("parameters", None):
            parameters = [Parameter.decode(p) for p in payload["parameters"]]
        else:
            parameters = None

        return Pipeline(
            id=payload.get("id", None),
            name=payload["name"],
            data_catalog=data_catalog,
            parameters=parameters,
            status=status,
            tags=tags,
            created_at=datetime.fromisoformat(
                payload["created_at"]) if payload.get("created_at", None) else None,
            parent=payload.get("parent", None),
            project_version=payload.get("project_version", None),
            pipeline_version=payload.get("pipeline_version", None),
            kedro_graphql_version=payload.get("kedro_graphql_version", None)
        )

    @classmethod
    def decode_pipeline_input(cls, payload):
        """Factory method to create a new Pipeline from a PipelineInput object.
        """
        d = jsonable_encoder(payload)
        return cls.decode_dict(d)


@strawberry.type
class Pipelines:
    pipelines: List[Pipeline] = strawberry.field(
        description="The list of pipeline instances.")
    page_meta: PageMeta = strawberry.field(description="Metadata to aid in pagination.")

    @classmethod
    def decode(cls, payload, decoder=None):
        """Factory method to create a new Pipelines from a graphql api response.
        """
        if decoder == "graphql":
            meta = {to_snake_case(k): v for k,
                    v in payload["readPipelines"]["pageMeta"].items()}
            return Pipelines(page_meta=PageMeta(**meta),
                             pipelines=[Pipeline.decode(p, decoder="graphql") for p in payload["readPipelines"]["pipelines"]])
        else:
            raise TypeError("decoder must be 'graphql'")


@strawberry.type
class PipelineEvent:
    id: str
    task_id: str
    status: str
    result: Optional[str] = None
    timestamp: str
    traceback: Optional[str] = None

    @classmethod
    def decode(cls, payload, decoder=None):
        """Factory method to create a new PipelineEvent from a graphql api response.
        """
        if decoder == "graphql":
            result = {to_snake_case(k): v for k, v in payload["pipeline"].items()}
            return PipelineEvent(**result)
        else:
            raise TypeError("decoder must be 'graphql'")


@strawberry.type
class PipelineLogMessage:
    id: str
    message: str
    message_id: str
    task_id: str
    time: str

    @classmethod
    def decode(cls, payload, decoder=None):
        """Factory method to create a new PipelineLogMessage from a graphql api response.
        """
        if decoder == "graphql":
            result = {to_snake_case(k): v for k, v in payload["pipelineLogs"].items()}
            return PipelineLogMessage(id=result["id"],
                                      message=result.get("message", ""),
                                      message_id=result.get("message_id", ""),
                                      task_id=result.get("task_id", ""),
                                      time=result.get("time", ""))
        else:
            raise TypeError("decoder must be 'graphql'")
