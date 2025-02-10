from kedro.framework.project import pipelines
from kedro.io import DataCatalog
#from kedro.runner import SequentialRunner
from typing import List, Dict
from kedro_graphql.runners import init_runner
from kedro_graphql.logs.logger import KedroGraphQLLogHandler
from celery import shared_task, Task
from .models import State
from datetime import datetime
from kedro.framework.session import KedroSession
import json

#from .backends import init_backend
#from .config import RUNNER
import logging
logger = logging.getLogger("kedro")

class KedroGraphqlTask(Task):

    _db = None

    @property
    def db(self):
        if self._db is None:
            #self._db = self._app.kedro_graphql_backend
            self._db = self.app.kedro_graphql_backend
        return self._db

    ## TO DO - modify these hooks to pass the status index -1 if possible to see if we can handle it here rather than in mongo backend 
    def before_start(self, task_id, args, kwargs):
        """Handler called before the task starts.

        .. versionadded:: 5.2

        Arguments:
            task_id (str): Unique id of the task to execute.
            args (Tuple): Original arguments for the task to execute.
            kwargs (Dict): Original keyword arguments for the task to execute.

        Returns:
            None: The return value of this handler is ignored.
        """
        handler = KedroGraphQLLogHandler(task_id, broker_url = self._app.conf["broker_url"])
        logger.addHandler(handler)

        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.STARTED
        p.status[-1].task_id = task_id
        p.status[-1].task_args = json.dumps(args)
        p.status[-1].task_kwargs = json.dumps(kwargs)
        self.db.update(p)


    def on_success(self, retval, task_id, args, kwargs):
        """Success handler.

        Run by the worker if the task executes successfully.

        Arguments:
            retval (Any): The return value of the task.
            task_id (str): Unique id of the executed task.
            args (Tuple): Original arguments for the executed task.
            kwargs (Dict): Original keyword arguments for the executed task.

        Returns:
            None: The return value of this handler is ignored.
        """
        
        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.SUCCESS
        self.db.update(p)
 


    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry handler.

        This is run by the worker when the task is to be retried.

        Arguments:
            exc (Exception): The exception sent to :meth:`retry`.
            task_id (str): Unique id of the retried task.
            args (Tuple): Original arguments for the retried task.
            kwargs (Dict): Original keyword arguments for the retried task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """
        
        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.RETRY
        p.status[-1].task_exception = str(exc)
        p.status[-1].task_einfo = str(einfo)
        self.db.update(p)        
   
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Error handler.

        This is run by the worker when the task fails.

        Arguments:
            exc (Exception): The exception raised by the task.
            task_id (str): Unique id of the failed task.
            args (Tuple): Original arguments for the task that failed.
            kwargs (Dict): Original keyword arguments for the task that failed.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        p = self.db.read(id=kwargs["id"])
        p.status[-1].state = State.FAILURE
        p.status[-1].task_exception = str(exc)
        p.status[-1].task_einfo = str(einfo)
        self.db.update(p)


    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Handler called after the task returns.

        Arguments:
            status (str): Current task state.
            retval (Any): Task return value/exception.
            task_id (str): Unique id of the task.
            args (Tuple): Original arguments for the task.
            kwargs (Dict): Original keyword arguments for the task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

        finished_at = datetime.now()

        p = self.db.read(id=kwargs["id"])
        p.status[-1].finished_at = finished_at
        p.status[-1].task_result = str(retval)
        self.db.update(p)

        logger.info("Closing log stream")
        for handler in logger.handlers:
            if isinstance(handler, KedroGraphQLLogHandler) and handler.topic == task_id:
                handler.flush()
                handler.close()
                handler.broker.connection.delete(task_id) ## delete stream
                handler.broker.connection.close()
        logger.handlers = []




@shared_task(bind = True, base = KedroGraphqlTask)
def run_pipeline(self, 
                 id: str = None,
                 name: str = None, 
                 inputs: dict = None, 
                 outputs: dict = None, 
                 parameters: dict = None, 
                 data_catalog: dict = None,
                 runner: str = None,
                 session_id: str = None,
                 slices: List[Dict[str, List[str]]] = None,
                 only_missing: bool = False):

    ## start
    if data_catalog:
        logger.info("using data_catalog parameter to build data catalog")
        io = DataCatalog().from_config(catalog = data_catalog)
    else:
        logger.info("using inputs and outputs parameters to build data catalog")
        logger.info("inputs: " + str(inputs))
        logger.info("outputs: " + str(outputs))
        catalog = {**inputs, **outputs}
        io = DataCatalog().from_config(catalog = catalog)

    ## add parameters to DataCatalog e.g. {"params:myparam":"value"}
    params = {"params:"+k:v for k,v in parameters.items()}
    params["parameters"] = parameters
    io.add_feed_dict(params)

    kedro_session = KedroSession(session_id=session_id)
    hook_manager = kedro_session._hook_manager

    try:
        hook_manager.hook.before_pipeline_run(
                run_params={
                    "pipeline_name": name
                }, pipeline=pipelines.get(name, None), catalog=io
            )
        runner = init_runner(runner = runner)

        if only_missing:
            # https://github.com/kedro-org/kedro/blob/06d5a6920cbb6b45c07dca6f77d14bb35e283b19/kedro/runner/runner.py#L154
            free_outputs = pipelines[name].outputs() - set(io.list())
            missing = {ds for ds in io.list() if not io.exists(ds)}
            to_build = free_outputs | missing
            to_rerun = pipelines[name].only_nodes_with_outputs(*to_build) + pipelines[name].from_inputs(
                *to_build
            )

            # We also need any missing datasets that are required to run the
            # `to_rerun` pipeline, including any chains of missing datasets.
            unregistered_ds = pipelines[name].datasets() - set(io.list())
            output_to_unregistered = pipelines[name].only_nodes_with_outputs(*unregistered_ds)
            input_from_unregistered = to_rerun.inputs() & unregistered_ds
            to_rerun += output_to_unregistered.to_outputs(*input_from_unregistered)

            p = self.db.read(id=id)
            p.status[-1].filtered_nodes = [node.name for node in to_rerun.nodes]
            self.db.update(p)

            runner().run(to_rerun, io, hook_manager)
        else:
            # Populate the filtering parameters based on the slices input
            tags = None
            from_nodes = None
            to_nodes = None
            node_names = None
            from_inputs = None
            to_outputs = None
            node_namespace = None

            if slices:            
                for slice_item in slices:
                    slice_type = slice_item['slice']
                    slice_args = slice_item['args']
                    
                    if slice_type == 'tags':
                        tags = slice_args
                    elif slice_type == 'from_nodes':
                        from_nodes = slice_args
                    elif slice_type == 'to_nodes':
                        to_nodes = slice_args
                    elif slice_type == 'node_names':
                        node_names = slice_args
                    elif slice_type == 'from_inputs':
                        from_inputs = slice_args
                    elif slice_type == 'to_outputs':
                        to_outputs = slice_args
                    elif slice_type == 'node_namespace':
                        node_namespace = slice_args[0]

            filtered_pipeline = pipelines[name].filter(
                tags=tags,
                from_nodes=from_nodes,
                to_nodes=to_nodes,
                node_names=node_names,
                from_inputs=from_inputs,
                to_outputs=to_outputs,
                node_namespace=node_namespace,
            )

            p = self.db.read(id=id)
            p.status[-1].filtered_nodes = [node.name for node in filtered_pipeline.nodes]
            self.db.update(p)

            runner().run(filtered_pipeline, catalog = io, hook_manager=hook_manager, session_id=session_id)

        return "success"
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        raise e
