import strawberry
from enum import Enum
from typing import List, Optional
import uuid
import json
from .config import config as CONFIG
from bson.objectid import ObjectId

def mark_deprecated(default = None):
    return strawberry.field(default = default, deprecation_reason="see " + str(CONFIG["KEDRO_GRAPHQL_DEPRECATIONS_DOCS"]))

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
        params =[]
        for k,v in parameters.items():
            ptype = type(v)

            if isinstance(ptype, int):
                ptype = ParameterType.INTEGER
            elif isinstance(ptype, float):
                ptype = ParameterType.FLOAT
            elif isinstance(ptype, bool):
                ptype = ParameterType.BOOLEAN
            else:
                ptype = ParameterType.STRING
            
            params.append(ParameterInput(name = k, value = str(v), type = ptype))
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

##    def serialize(self) -> dict:
##        """
##        Returns serializable dict in format compatible with kedro.
##        """
##        values = {}
##        for v in self.value:
##            values.update(v.serialize())
##        return {self.name: values}
##
##    def merge(self, a, b, path=None):
##        "merges nested dictionaries recursively.  Merges b into a."
##        if path is None: path = []
##        for key in b:
##            if key in a:
##                if isinstance(a[key], dict) and isinstance(b[key], dict):
##                    self.merge(a[key], b[key], path + [str(key)])
##                elif a[key] == b[key]:
##                    pass # same leaf value
##                else:
##                    raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
##            else:
##                a[key] = b[key]
##        return a
    
@strawberry.type
class DataSet:
    name: str
    config: Optional[str] = None
    type: Optional[str] = mark_deprecated(default = None)
    filepath: Optional[str] = mark_deprecated(default = None)
    save_args: Optional[List[Parameter]] = mark_deprecated(default = None)
    load_args: Optional[List[Parameter]] = mark_deprecated(default = None)
    credentials: Optional[str] = None

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        temp = self.__dict__.copy()
        temp.pop("name")
        if temp.get("config", None):
            return {self.name: json.loads(temp['config'])}
        else:
            temp.pop("config")
            if not temp["save_args"]:
                temp.pop("save_args")
            else:
                temp["save_args"] = {k:v for p in self.__dict__["save_args"] for k,v in p.serialize().items() }
            if not temp["load_args"]:
                temp.pop("load_args")
            else:
                temp["load_args"] = {k:v for p in self.__dict__["save_args"] for k,v in p.serialize().items() }
        return {self.name: temp}

    @staticmethod
    def from_dict(payload):
        """
        Return a new DataSet from a dictionary.

        Args:
            payload (dict): dict representing DataSet e.g.

                {
                  "name": "text_in",
                  "filepath": "./data/01_raw/text_in.txt",
                  "type": "text.TextDataSet",
                  "save_args":[{"name": "say", "value": "hello"}],
                  "load_args":[{"name": "say", "value": "hello"}]
                }

                or

                {
                  "name": "text_in",
                  "config":  '{"filepath": "./data/01_raw/text_in.txt", "type": "text.TextDataSet", "save_args": [{"name": "say", "value": "hello"}], "load_args": [{"name": "say", "value": "hello"}]}'
                }

        """
        if payload.get("config", False):
            return DataSet(
                name = payload["name"],
                config = payload["config"]
            )

        else:
            if payload.get("save_args", False):
                save_args = [Parameter(**p) for p in payload["save_args"]]
            else:
                save_args = None
                
            if payload.get("load_args", False):
                load_args = [Parameter(**p) for p in payload["load_args"]]
            else:
                load_args = None

            return DataSet(
                name = payload["name"],
                type = payload["type"],
                filepath = payload["filepath"],
                save_args = save_args,
                load_args = load_args
            )


@strawberry.input
class DataSetInput:
    name: str
    config: Optional[str] = None
    type: Optional[str] = mark_deprecated(default = None)
    filepath: Optional[str] = mark_deprecated(default = None)
    save_args: Optional[List[ParameterInput]] = mark_deprecated(default = None)
    load_args: Optional[List[ParameterInput]] = mark_deprecated(default = None)
    credentials: Optional[str] = None
        

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
        return [DataSetInput(name = k, config = json.dumps(v)) for k,v in config.items()]

@strawberry.type
class Node:
    name: str
    inputs: List[str]
    outputs: List[str]
    tags: List[str]

@strawberry.type(description = "PipelineTemplates are definitions of Pipelines.  They represent the supported interface for executing a Pipeline.")
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

        return [Node(name = n.name, inputs = n.inputs, outputs = n.outputs, tags = n.tags) for n in nodes]

    @strawberry.field
    def parameters(self) -> List[Parameter]:
        ## keep track of parameters to avoid returning duplicates    
        params = {}
        for n in self.kedro_pipelines[self.name].all_inputs():
            if n.startswith("params:"):
                name = n.split("params:")[1]
                value = self.kedro_parameters[name]
                if not params.get(name, False):
                    params[name] = value
            elif n == "parameters":
                for k,v in self.kedro_parameters.items():
                    if not params.get(k, False):
                        params[k] = v
        return [Parameter(name = k, value = v) for k,v in params.items()]

    @strawberry.field
    def inputs(self) -> List[DataSet]:
        inputs_resolved = []
        for n in self.kedro_pipelines[self.name].all_inputs():
            if not n.startswith("params:") and n != "parameters":
                config = self.kedro_catalog[n]
                #inputs_resolved.append(DataSet(name = n, filepath = config["filepath"], type = config["type"], save_args = config.get("save_args", None), load_args = config.get("load_args", None)))
                inputs_resolved.append(DataSet(name = n, config = json.dumps(config)))
            
        return inputs_resolved
 
    @strawberry.field
    def outputs(self) -> List[DataSet]:
        outputs_resolved = []
        for n in self.kedro_pipelines[self.name].all_outputs():    
            config = self.kedro_catalog[n]
            #outputs_resolved.append(DataSet(name = n, filepath = config["filepath"], type = config["type"], save_args = config.get("save_args", None), load_args = config.get("load_args", None)))
            outputs_resolved.append(DataSet(name = n, config = json.dumps(config)))
 
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
        for k,v in kedro_pipelines.items():
            pipes.append(PipelineTemplate(name = k,
                                          id = ObjectId(str(count)), 
                                          kedro_pipelines = kedro_pipelines,
                                          kedro_catalog = kedro_catalog,
                                          kedro_parameters = kedro_parameters))
            count +=1

        return pipes



@strawberry.input(description = "PipelineInput")
class PipelineInput:
    name: str
    parameters: Optional[List[ParameterInput]] = None
    inputs: Optional[List[DataSetInput]] = mark_deprecated(default = None)
    outputs: Optional[List[DataSetInput]] = mark_deprecated(default = None)
    data_catalog: Optional[List[DataSetInput]] = None
    tags: Optional[List[TagInput]] = None
    #credentials: Optional[List[CredentialInput]] = None
    #credentials_nested: Optional[List[CredentialNestedInput]] = None

    @staticmethod
    def create(name = None, data_catalog = None, parameters = None, tags = None):
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
                          inputs=None, 
                          outputs=None, 
                          data_catalog=[
                            DataSetInput(name='text_in', config='{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}', type=None, filepath=None, save_args=None, load_args=None, credentials=None), 
                            DataSetInput(name='text_out', config='{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}', type=None, filepath=None, save_args=None, load_args=None, credentials=None)
                          ], 
                          tags=[TagInput(key='owner', value='sean')])

            print(jsonable_encoder(p))

            ## this can be used as the PipelineInput parameter when calleing the pipeline mutation via the API
            {'name': 'example00',
            'parameters': [{'name': 'example', 'value': 'hello', 'type': 'string'},
             {'name': 'duration', 'value': '1', 'type': 'string'}],
            'inputs': None,
            'outputs': None,
            'data_catalog': [{'name': 'text_in',
              'config': '{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}',
              'type': None,
              'filepath': None,
              'save_args': None,
              'load_args': None,
              'credentials': None},
             {'name': 'text_out',
              'config': '{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}',
              'type': None,
              'filepath': None,
              'save_args': None,
              'load_args': None,
              'credentials': None}],
            'tags': [{'key': 'owner', 'value': 'sean'}],
            'credentials': None,
            'credentials_nested': None}

        """
        if tags:
            tags = [TagInput(key = k, value = v) for t in tags for k,v in t.items()]
         
        if data_catalog:
            data_catalog = DataCatalogInput.create(data_catalog)

        if parameters:
            parameters = ParameterInput.create(parameters)

        return PipelineInput(name = name,
                             parameters = parameters,
                             data_catalog = data_catalog,
                             tags = tags)


## Should expand pipeline type to include pipeline version
@strawberry.type
class Pipeline:
    #kedro_pipelines: strawberry.Private[Optional[dict]] = None
    #kedro_catalog: strawberry.Private[Optional[dict]] = None
    #kedro_parameters: strawberry.Private[Optional[dict]] = None
    kedro_pipelines_index: strawberry.Private[Optional[List[PipelineTemplate]]] = None

    id: Optional[uuid.UUID] = None
    inputs: Optional[List[DataSet]] = mark_deprecated(default= None)
    name: str
    outputs: Optional[List[DataSet]] = mark_deprecated(default= None)
    data_catalog: Optional[List[DataSet]] = None
    parameters: List[Parameter]
    status: Optional[str] = None
    tags: Optional[List[Tag]] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    task_args: Optional[str] = None
    task_kwargs: Optional[str] = None
    task_request: Optional[str] = None
    task_exception: Optional[str] = None
    task_traceback: Optional[str] = None
    task_einfo: Optional[str] = None
    task_result: Optional[str] = None

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
        inputs = {}
        outputs = {}
        parameters = {}
        data_catalog = {}
        if self.inputs:
             for i in self.inputs:
                 s = i.serialize()
                 inputs.update(s)

        if self.outputs:
            for o in self.outputs:
                s = o.serialize()
                outputs.update(s)

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
            "inputs": inputs,
            "outputs": outputs,
            "data_catalog": data_catalog,
            "parameters": parameters,
        }

    @staticmethod
    def from_dict(payload):
        if payload.get("tags", None):
            tags = [Tag(**t) for t in payload["tags"]]
        else:
            tags = None
         
        if payload.get("data_catalog", None):
            data_catalog = [DataSet.from_dict(d) for d in payload["data_catalog"]]
        else:
            data_catalog = None

        if payload.get("inputs", None):
            inputs = [DataSet.from_dict(i) for i in payload["inputs"]]
        else:
            inputs = None

        if payload.get("outputs", None):
            outputs = [DataSet.from_dict(o) for o in payload["outputs"]]
        else:
            outputs = None

        return Pipeline(
            id = payload.get("id", None),
            name = payload["name"],
            inputs = inputs,
            outputs = outputs,
            data_catalog = data_catalog,
            parameters = [Parameter(**p) for p in payload["parameters"]],
            status = payload.get("status", None),
            tags = tags,
            task_id = payload.get("task_id", None),
            task_name = payload.get("task_name", None),
            task_args = payload.get("task_args", None),
            task_kwargs = payload.get("task_kwargs", None),
            task_request = payload.get("task_request", None),
            task_exception = payload.get("task_exception", None),
            task_traceback = payload.get("task_traceback", None),
            task_einfo = payload.get("task_einfo", None),
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
