import logging
from importlib import import_module

logger = logging.getLogger("kedro")


def get_runner_class(runner_import_path: str):
    module, class_name = runner_import_path.rsplit(".", 1)
    module = import_module(module)
    return getattr(module, class_name)


def init_runner(runner_import_path: str, **runner_kwargs):
    runner_cls = get_runner_class(runner_import_path)
    logger.info("using runner " + str(runner_cls))
    return runner_cls(**runner_kwargs)
