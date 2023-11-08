from importlib import import_module
import logging
logger = logging.getLogger("kedro")


def init_runner(runner = None):
    module, class_name = runner.rsplit(".", 1)

    module = import_module(module)
    runner_cls = getattr(module, class_name)
    logger.info("using runner " + str(runner_cls))
    return runner_cls