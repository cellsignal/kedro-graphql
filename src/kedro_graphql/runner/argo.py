from kedro.io import AbstractDataSet, DataCatalog, MemoryDataSet
from kedro.pipeline import Pipeline
from kedro.runner.runner import AbstractRunner, run_node
from pluggy import PluginManager


class ArgoWorkflowsRunner(AbstractRunner):
    """``ArgoWorkflowsRunner`` is an ``AbstractRunner`` implementation. It can be used
    to run pipelines on [argo workflows](https://argoproj.github.io/argo-workflows/).
    """

    def create_default_data_set(self, ds_name: str) -> AbstractDataSet:
        """Factory method for creating the default data set for the runner.

        NOTE THIS SHOULD BE CHANGED TO SOMETHING S3 COMPATIBLE.

        Args:
            ds_name: Name of the missing data set
        Returns:
            An instance of an implementation of AbstractDataSet to be used
            for all unregistered data sets.

        """
        return MemoryDataSet()

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

        ## SequentialRunner source code below this line:
        nodes = pipeline.nodes
        done_nodes = set()

        load_counts = Counter(chain.from_iterable(n.inputs for n in nodes))

        for exec_index, node in enumerate(nodes):
            try:
                run_node(node, catalog, hook_manager, self._is_async, session_id)
                done_nodes.add(node)
            except Exception:
                self._suggest_resume_scenario(pipeline, done_nodes, catalog)
                raise

            # decrement load counts and release any data sets we've finished with
            for data_set in node.inputs:
                load_counts[data_set] -= 1
                if load_counts[data_set] < 1 and data_set not in pipeline.inputs():
                    catalog.release(data_set)
            for data_set in node.outputs:
                if load_counts[data_set] < 1 and data_set not in pipeline.outputs():
                    catalog.release(data_set)

            self._logger.info(
                "Completed %d out of %d tasks", exec_index + 1, len(nodes)
            )

        
    def workflow_template(self):
        """
        https://docs.kedro.org/en/stable/deployment/argo.html
        """
        pass

    def stream_logs(self):
        """https://github.com/argoproj/argo-workflows/issues/4017
        """
        pass

    def submit_workflow(self):
        pass

    def workflow_status(self):
        pass
        