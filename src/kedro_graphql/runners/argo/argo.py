
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import re

import requests
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from kedro.io import AbstractDataset, DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.runner.runner import AbstractRunner
from pluggy import PluginManager


class ArgoWorkflowsRunner(AbstractRunner):
    """``ArgoWorkflowsRunner`` is an ``AbstractRunner`` implementation. It can be used
    to run pipelines on [argo workflows](https://argoproj.github.io/argo-workflows/).
    """
    supports_memory_datasets = False

    ## NEED TO ADD TO kedro_graphq.config
    namespace = "default"
    host = "http://127.0.0.1:2746"
    endpoints = {"get_workflow": "/api/v1/workflows/{namespace}/{name}",
                 "create_workflow": "/api/v1/workflows/{namespace}",
                 "workflow_logs": "/api/v1/workflows/{namespace}/{name}/log"}
    image = "docker/whalesay:latest"
    package_name = "kedro-graphql"
    env = Environment(
        loader=PackageLoader("kedro_graphql.runners.argo"), autoescape=select_autoescape()
    )

    def _get_executor(self, max_workers: int):
        return ThreadPoolExecutor(max_workers=max_workers)

    def create_default_data_set(self, ds_name: str) -> AbstractDataset:
        """Factory method for creating the default data set for the runner.

        NOTE THIS SHOULD BE CHANGED TO SOMETHING S3 COMPATIBLE.

        Args:
            ds_name: Name of the missing data set
        Returns:
            An instance of an implementation of AbstractDataSet to be used
            for all unregistered data sets.

        """
        return MemoryDataset()

    def _run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager = None,
        session_id: str = None,
    ) -> None:
        """The method implementing argo workflows pipeline running.
        Example logs output using this implementation:

         

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            session_id: The id of the session.

        """
        nodes = pipeline.nodes
        self._logger.info(
            "Actual run will execute %s nodes:\n%s",
            len(nodes),
            pipeline.describe(),
        )
        self._logger.info("Checking inputs...")
        input_names = pipeline.inputs()
        missing_inputs = [
            input_name
            for input_name in input_names
            if not catalog._get_dataset(input_name).exists()
        ]
        if missing_inputs:
            raise KeyError(f"Datasets {missing_inputs} not found.")


        tasks = self.get_dependencies(pipeline.node_dependencies)

        template = self.env.get_template("argo_spec.tmpl")
        output = template.render(
            image=self.image,
            package_name=self.package_name,
            tasks=tasks,
            pipeline_id=self._label_value(self.run_context["pipeline_id"]),
            task_id=self._label_value(self.run_context["task_id"]),
        )
        manifest =  yaml.safe_load(output)
        
        
        resp0 = self.create_workflow(manifest)
        self.emit_metadata(self._workflow_metadata(resp0))

        ## stream argo logs to kedro logger
        self.workflow_logs(resp0["metadata"]["name"])

        resp1 = self.get_workflow(resp0["metadata"]["name"])
        self.emit_metadata(self._workflow_metadata(resp1))

        self._logger.info("Completed " + resp1["status"]["progress"] + " tasks")

        if resp1["status"]["phase"] == "Failed":
            raise RuntimeError()
        
        ## need to check out status types and reconnect if still running, maybe while loop?
        ## also what happens when connection to argo server is lost during call
        ## to workflow_logs, how to restablish etc...

    def clean_name(self, name):
        return re.sub(r"[\W_]+", "-", name).strip("-")

    def _label_value(self, value):
        value = re.sub(r"[^A-Za-z0-9_.-]", "-", str(value)).strip("-_.")[:63]
        if not value:
            raise ValueError("Argo correlation label cannot be empty")
        return value.rstrip("-_.")

    def _workflow_metadata(self, response):
        metadata = response["metadata"]
        submitted_at = datetime.fromisoformat(
            metadata["creationTimestamp"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        values = {
            "x-argo-namespace": metadata["namespace"],
            "x-argo-workflow-name": metadata["name"],
            "x-argo-workflow-uid": metadata["uid"],
            "x-argo-submitted-at": submitted_at.isoformat(),
            "x-argo-reconciled-at": datetime.now(timezone.utc).isoformat(),
        }
        phase = response.get("status", {}).get("phase")
        if phase is not None:
            values["x-argo-phase"] = phase
        return values

    def create_workflow(self, manifest):
        """
        
        """
        endpoint = self.host + self.endpoints["create_workflow"].format(namespace = self.namespace)
        resp = requests.post(url = endpoint, json = {"workflow":manifest})
        resp.raise_for_status()
        return resp.json()

        
    def get_dependencies(self, dependencies):
        deps_dict = [
            {
                "node": node.name,
                "name": self.clean_name(node.name),
                "deps": [self.clean_name(val.name) for val in parent_nodes],
            }
            for node, parent_nodes in dependencies.items()
        ]
        return deps_dict

    def get_workflow(self, name):
        """
        
        """
        endpoint = self.host + self.endpoints["get_workflow"].format(namespace = self.namespace, name = name)
        resp = requests.get(url = endpoint)
        resp.raise_for_status()
        return resp.json()


    def workflow_logs(self, name):
        """
        
        Inspired by https://github.com/argoproj/argo-workflows/issues/4017


        """
        endpoint = self.host + self.endpoints["workflow_logs"].format(namespace = self.namespace, name = name)
        params = {
            'logOptions.container': 'main',
            'logOptions.follow': True
        }
        with requests.get(url=endpoint, params=params, stream=True) as resp:
            for _line in resp.iter_lines():
                self._logger.info(json.loads(_line.decode())["result"]["content"])
