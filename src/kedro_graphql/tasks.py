from kedro.framework.project import pipelines
from kedro.io import DataCatalog
from kedro import __version__ as kedro_version
#from kedro.runner import SequentialRunner
from kedro_graphql.runners import init_runner
from kedro_graphql.logs.logger import KedroGraphQLLogHandler
from celery import shared_task, Task
from .models import State, DataSet
from datetime import datetime, date
from kedro.framework.session import KedroSession
from fastapi.encoders import jsonable_encoder
from .config import config as CONFIG
import json
from kedro.io import AbstractDataset
from pathlib import Path

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

        p = self.db.update(task_id=task_id, values = {"status": {"state": State.STARTED}})

        try:
            # Ensure LOG_PATH_PREFIX is provided
            log_path_prefix = CONFIG.get('LOG_PATH_PREFIX')
            if log_path_prefix:

                today = date.today()

                # Add metadata and log datasets to data catalog
                gql_meta = DataSet(name="gql_meta", config=json.dumps({"type": "json.JSONDataset",
                                                            "filepath":f"{CONFIG['LOG_PATH_PREFIX']}/year={today.year}/month={today.month}/day={today.day}/{p.id}/meta.json"}))
                gql_logs = DataSet(name="gql_logs",config=json.dumps({"type": "partitions.PartitionedDataset",
                                                        "dataset": "text.TextDataset",
                                                        "path": f"{CONFIG['LOG_PATH_PREFIX']}/year={today.year}/month={today.month}/day={today.day}/{p.id}/"}))
                p.data_catalog.append(gql_meta)
                p.data_catalog.append(gql_logs)

                # Save metadata to S3
                AbstractDataset.from_config(gql_meta.name, json.loads(gql_meta.config)).save(p.serialize())
                p = self.db.update(p.id, values={"data_catalog": jsonable_encoder(p.data_catalog)})

                logger.info(f"Capturing pipeline metadata in {CONFIG['LOG_PATH_PREFIX']}/year={today.year}/month={today.month}/day={today.day}/{p.id}/meta.json")
                logger.info(f"Capturing pipeline logs in {CONFIG['LOG_PATH_PREFIX']}/year={today.year}/month={today.month}/day={today.day}/{p.id}/logs")

                # Capture pipeline object returned as an attribute of the task object
                setattr(self, "kedro_graphql_pipeline", p)
            else:
                logger.info(f"Missing LOG_PATH_PREFIX in config. Not capturing logs in S3.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")


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
        
        self.db.update(task_id=task_id, values = {"status": {"state": State.SUCCESS, "task_exception": None, "task_einfo": None}})


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
        
        self.db.update(task_id=task_id, values = {"status": {"state": State.RETRY, "task_exception": str(exc), "task_einfo": str(einfo)}})
   
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

        self.db.update(task_id=task_id, values = {"status": {"state": State.FAILURE, "task_exception": str(exc), "task_einfo": str(einfo)}})

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
        self.db.update(task_id=task_id, values = {"status": {"finished_at": finished_at, "task_result": str(retval)}})

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
                 name: str = None, 
                 inputs: dict = None, 
                 outputs: dict = None, 
                 parameters: dict = None, 
                 data_catalog: dict = None,
                 runner: str = None):
    with KedroSession.create(project_path = Path(__file__).resolve().parent.parent.parent,
                             env = CONFIG["KEDRO_GRAPHQL_ENV"],
                             conf_source = CONFIG["KEDRO_GRAPHQL_CONF_SOURCE"]) as session:
        
        # If modified data catalog object with gql_meta and gql_logs datasets exists, use it
        if getattr(self, "kedro_graphql_pipeline", None):
            logger.info("using data_catalog with gql_meta and gql_logs")
            catalog = {}
            for dataset in self.kedro_graphql_pipeline.data_catalog:
                dataset.serialize()
                catalog[dataset.name] = json.loads(dataset.config)
            io = DataCatalog().from_config(catalog = catalog)
        elif data_catalog:
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

        hook_manager = session._hook_manager

        record_data = {
                "session_id": session.session_id,
                "project_path": session._project_path.as_posix(),
                "env": session.load_context().env,
                "kedro_version": kedro_version,
                "tags": "", # Construct the pipeline using only nodes which have this tag attached.
                "from_nodes": "", # A list of node names which should be used as a starting point.
                "to_nodes": "", # A list of node names which should be used as an end point.
                "node_names": "", # Run only nodes with specified names.
                "from_inputs": "", # A list of dataset names which should be used as a starting point.
                "to_outputs": "", # A list of dataset names which should be used as an end point.
                "load_versions": "", # Specify a particular dataset version (timestamp) for loading
                "extra_params": "", # Specify extra parameters that you want to pass to the context initialiser.
                "pipeline_name": name,
                "namespace": "", # Name of the node namespace to run.
                "runner": getattr(runner, "__name__", str(runner)),
            }

        try:
            hook_manager.hook.before_pipeline_run(
                    run_params=record_data,
                    pipeline=pipelines.get(name, None),
                    catalog=io
                )
            runner = init_runner(runner = runner)
            run_result = runner().run(pipelines[name], catalog = io, hook_manager=hook_manager, session_id=session.session_id)

            hook_manager.hook.after_pipeline_run(
                    run_params=record_data,
                    run_result=run_result,
                    pipeline=pipelines.get(name, None),
                    catalog=io
                )

            return "success"
        except Exception as e:
            logger.exception(f"Error running pipeline: {e}")
            hook_manager.hook.on_pipline_error(
                error = e,
                run_params=record_data,
                pipeline=pipelines.get(name, None),
                catalog=io
            )
            raise e
