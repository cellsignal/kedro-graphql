import logging
from importlib import import_module

logger = logging.getLogger("kedro")


def init_runner(runner_import_path: str, **runner_kwargs):
    module, class_name = runner_import_path.rsplit(".", 1)

    module = import_module(module)
    runner_cls = getattr(module, class_name)
    logger.info("using runner " + str(runner_cls))
    return runner_cls(**runner_kwargs)
