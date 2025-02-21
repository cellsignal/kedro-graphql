import json
import uuid
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import List, Optional

import boto3
import strawberry
from botocore.exceptions import ClientError
from bson.objectid import ObjectId
from fastapi.encoders import jsonable_encoder
from kedro.io import AbstractDataset
from strawberry.scalars import JSON

from .config import config as CONFIG
from .utils import parse_s3_filepath


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
        if input_dict.get("type", True):
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
                raise ValueError("Parameter of type BOOL must be one of 'True', 'true', 'False', or 'false'")

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
        params = []
        for k, v in parameters.items():
            ptype = type(v)

            if isinstance(ptype, int):
                ptype = ParameterType.INTEGER
            elif isinstance(ptype, float):
                ptype = ParameterType.FLOAT
            elif isinstance(ptype, bool):
                ptype = ParameterType.BOOLEAN
            else:
                ptype = ParameterType.STRING

            params.append(ParameterInput(name=k, value=str(v), type=ptype))
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

# def serialize(self) -> dict:
# """
# Returns serializable dict in format compatible with kedro.
# """
# values = {}
# for v in self.value:
# values.update(v.serialize())
# return {self.name: values}
##
# def merge(self, a, b, path=None):
# "merges nested dictionaries recursively.  Merges b into a."
# if path is None: path = []
# for key in b:
# if key in a:
# if isinstance(a[key], dict) and isinstance(b[key], dict):
# self.merge(a[key], b[key], path + [str(key)])
# elif a[key] == b[key]:
# pass # same leaf value
# else:
# raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
# else:
# a[key] = b[key]
# return a


@strawberry.type
class DataSet:
    name: str
    config: Optional[str] = None
    tags: Optional[List[Tag]] = None

    @strawberry.field
    def pre_signed_url_create(self) -> Optional[JSON]:
        """
        Generate a presigned URL S3 to upload a file.

        Returns:
            Optional[JSON]: Dictionary with the URL to post to and form fields and values to submit with the POST. If an error occurs, returns None.

            Example:
                {
                    "url": "https://your-bucket-name.s3.amazonaws.com/",
                    "fields": {
                        "key": "your-object-key",
                        "AWSAccessKeyId": "your-access-key-id",
                        "x-amz-security-token": "your-security-token",
                        "policy": "your-policy",
                        "signature": "your-signature"
                    }
                }
        """

        bucket_name, s3_key = parse_s3_filepath(self.config)

        try:
            s3_client = boto3.client('s3')
            response = s3_client.generate_presigned_post(bucket_name,
                                                         f"{uuid.uuid4()}/{s3_key}",
                                                         Fields=None,
                                                         Conditions=None,
                                                         ExpiresIn=3600)
        except ClientError as e:
            print(f"Failed to generate presigned URL: {e}")
            return None

        return response

    @strawberry.field
    def pre_signed_url_read(self) -> Optional[str]:
        """
        Generate a presigned URL S3 to download a file.

        Returns:
            Optional[str]: download url with query parameters

            Example: https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time
        """

        bucket_name, s3_key = parse_s3_filepath(self.config)

        try:
            s3_client = boto3.client('s3')
            params = {
                'Bucket': bucket_name,
                'Key': s3_key
            }

            response = s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=3600
            )
        except ClientError as e:
            print(f"Failed to generate presigned URL: {e}")
            return None

        return response

    @strawberry.field
    def exists(self) -> bool:
        if self.config:
            return AbstractDataset.from_config(self.name, json.loads(self.config)).exists()
        else:
            return False

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


@strawberry.input
class DataSetInput:
    name: str
    config: Optional[str] = None
    tags: Optional[List[TagInput]] = None


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
            config = self.kedro_catalog[n]
            outputs_resolved.append(DataSet(name=n, config=json.dumps(config)))

        return outputs_resolved


@strawberry.type
class PageMeta:
    next_cursor: Optional[str] = strawberry.field(
        description="The next cursor to continue with."
    )


@strawberry.type
class PipelineTemplates:
    pipeline_templates: List[PipelineTemplate] = strawberry.field(description="The list of pipeline templates.")

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
    # credentials: Optional[List[CredentialInput]] = None
    # credentials_nested: Optional[List[CredentialNestedInput]] = None
    parent: Optional[uuid.UUID] = None
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
                            DataSetInput(name='text_in', config='{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}'), 
                            DataSetInput(name='text_out', config='{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}')
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
            tags = [TagInput(key=k, value=v) for t in tags for k, v in t.items()]

        if data_catalog:
            data_catalog = DataCatalogInput.create(data_catalog)

        if parameters:
            parameters = ParameterInput.create(parameters)

        return PipelineInput(name=name,
                             parameters=parameters,
                             data_catalog=data_catalog,
                             tags=tags)


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
    # the kedro session https://docs.kedro.org/en/stable/kedro_project_setup/session.html, tracking the session id allows us to find the related logs see https://cellsignal.atlassian.net/browse/BIOINDS-529
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


# Should expand pipeline type to include pipeline version
@strawberry.type
class Pipeline:
    # kedro_pipelines: strawberry.Private[Optional[dict]] = None
    # kedro_catalog: strawberry.Private[Optional[dict]] = None
    # kedro_parameters: strawberry.Private[Optional[dict]] = None
    kedro_pipelines_index: strawberry.Private[Optional[List[PipelineTemplate]]] = None
    id: Optional[uuid.UUID] = None
    name: str
    data_catalog: Optional[List[DataSet]] = None
    parameters: Optional[List[Parameter]] = None
    status: List[PipelineStatus] = strawberry.field(default_factory=list)
    tags: Optional[List[Tag]] = None
    created_at: Optional[datetime] = None
    parent: Optional[uuid.UUID] = None
    project_version: Optional[str] = None
    pipeline_version: Optional[str] = None
    kedro_graphql_version: Optional[str] = None

    @strawberry.field
    def template(self) -> PipelineTemplate:
        for p in self.kedro_pipelines_index:
            if p.name == self.name:
                return p

    @strawberry.field
    def describe(self) -> str:
        return self.template().describe()

    @strawberry.field
    def nodes(self) -> List[Node]:
        return self.template().nodes()

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
            "id": self.id,
            "name": self.name,
            "data_catalog": data_catalog,
            "parameters": parameters,
        }

    def encode(self, encoder="dict"):

        if encoder == "dict":
            p = deepcopy(self)
            p.id = str(p.id)  # if type ObjectID the jsonable_encoder will throw an error
            encoded_pipeline = jsonable_encoder(p)

            # remove fields we dont want to encode
            encoded_pipeline.pop("kedro_pipelines_index")
            return encoded_pipeline
        elif encoder == "kedro":
            return self.serialize()
        else:
            raise TypeError("encoder must be 'dict' or 'kedro'")

    @staticmethod
    def decode(payload):
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
                started_at=datetime.fromisoformat(s["started_at"]) if s.get("started_at") else None,
                finished_at=datetime.fromisoformat(s["finished_at"]) if s.get("finished_at") else None,
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
            created_at=datetime.fromisoformat(payload["created_at"]) if payload.get("created_at", None) else None,
            parent=payload.get("parent", None),
            project_version=payload.get("project_version", None),
            pipeline_version=payload.get("pipeline_version", None),
            kedro_graphql_version=payload.get("kedro_graphql_version", None)
        )


@strawberry.type
class Pipelines:
    pipelines: List[Pipeline] = strawberry.field(description="The list of pipeline instances.")
    page_meta: PageMeta = strawberry.field(description="Metadata to aid in pagination.")


@strawberry.type
class PipelineEvent:
    id: str
    task_id: str
    status: str
    result: Optional[str] = None
    timestamp: str
    traceback: Optional[str] = None


@strawberry.type
class PipelineLogMessage:
    id: str
    message: str
    message_id: str
    task_id: str
    time: str
