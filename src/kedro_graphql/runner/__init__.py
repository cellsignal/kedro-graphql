
from kedro_graphql.config import config
from importlib import import_module
import logging
logger = logging.getLogger("kedro")

def init_runner(runner = None):
    if runner:
        module, class_name = runner.rsplit(".", 1)
    else:
        module, class_name = config["KEDRO_GRAPHQL_RUNNER"].rsplit(".", 1)

    module = import_module(module)
    runner_cls = getattr(module, class_name)
    logger.info("using runner " + str(runner_cls))
    return runner_cls