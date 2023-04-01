import strawberry
from typing import List, Optional
import uuid
from .config import conf_catalog, conf_parameters, PIPELINES

@strawberry.type
class Parameter:
    name: str
    value: str

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        return {self.name: self.value}

@strawberry.input
class ParameterInput:
    name: str
    value: str

@strawberry.type
class DataSet:
    name: str
    type: str
    filepath: str
    save_args: Optional[List[Parameter]] = None
    load_args: Optional[List[Parameter]] = None

    def serialize(self) -> dict:
        """
        Returns serializable dict in format compatible with kedro.
        """
        temp = self.__dict__.copy()
        temp.pop("name")
        if not temp["save_args"]:
            temp.pop("save_args")
        if not temp["load_args"]:
            temp.pop("load_args")
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

        """

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
    type: str
    filepath: str
    save_args: Optional[List[ParameterInput]] = None
    load_args: Optional[List[ParameterInput]] = None

@strawberry.type
class Node:
    name: str
    inputs: List[str]
    outputs: List[str]
    tags: List[str]

@strawberry.type(description = "PipelineTemplates are definitions of Pipelines.  They represent the supported interface for executing a Pipeline.")
class PipelineTemplate:
    name: str

    @strawberry.field
    def describe(self) -> str:
        return PIPELINES[self.name].describe()

    @strawberry.field
    def nodes(self) -> List[Node]:
        nodes = PIPELINES[self.name].nodes

        return [Node(name = n.name, inputs = n.inputs, outputs = n.outputs, tags = n.tags) for n in nodes]

    @strawberry.field
    def parameters(self) -> List[Parameter]:
        ## keep track of parameters to avoid returning duplicates    
        params = {}
        for n in PIPELINES[self.name].inputs():
            if n.startswith("params:"):
                name = n.split("params:")[1]
                value = conf_parameters[name]
                if not params.get(name, False):
                    params[name] = value
            elif n == "parameters":
                for k,v in conf_parameters.items():
                    if not params.get(k, False):
                        params[k] = v
        return [Parameter(name = k, value = v) for k,v in params.items()]

    @strawberry.field
    def inputs(self) -> List[DataSet]:
        inputs_resolved = []
        for n in PIPELINES[self.name].inputs():
            if not n.startswith("params:") and n != "parameters":
                config = conf_catalog[n]
                inputs_resolved.append(DataSet(name = n, filepath = config["filepath"], type = config["type"], save_args = config.get("save_args", None), load_args = config.get("load_args", None)))
            
        return inputs_resolved
 
    @strawberry.field
    def outputs(self) -> List[DataSet]:
        outputs_resolved = []
        for n in PIPELINES[self.name].outputs():    
            config = conf_catalog[n]
            outputs_resolved.append(DataSet(name = n, filepath = config["filepath"], type = config["type"], save_args = config.get("save_args", None), load_args = config.get("load_args", None)))
 
        return outputs_resolved

@strawberry.input(description = "PipelineInput")
class PipelineInput:
    name: str
    parameters: List[ParameterInput]
    inputs: List[DataSetInput]
    outputs: List[DataSetInput]

@strawberry.type
class Pipeline:
    id: Optional[uuid.UUID] = None
    inputs: List[DataSet]
    name: str
    outputs: List[DataSet]
    parameters: List[Parameter]
    status: Optional[str] = None
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
        return PipelineTemplate(name = self.name)

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
        for i in self.inputs:
            s = i.serialize()
            inputs.update(s)

        for o in self.outputs:
            s = o.serialize()
            outputs.update(s)

        for p in self.parameters:
            s = p.serialize()
            parameters.update(s)

        return {
            "id": self.id,
            "name": self.name,
            "inputs": inputs,
            "outputs": outputs,
            "parameters": parameters,
        }

    @staticmethod
    def from_dict(payload):
        return Pipeline(
            id = payload.get("id", None),
            name = payload["name"],
            inputs = [DataSet.from_dict(i) for i in payload["inputs"]],
            outputs = [DataSet.from_dict(o) for o in payload["outputs"]],
            parameters = [Parameter(**p) for p in payload["parameters"]],
            status = payload.get("status", None),
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
class PipelineEvent:
    id: str
    task_id: str
    status: str
    result: Optional[str] = None
    timestamp: str
    traceback: Optional[str] = None

