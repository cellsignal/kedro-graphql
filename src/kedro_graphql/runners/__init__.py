import logging
from importlib import import_module

logger = logging.getLogger("kedro")
from kedro.runner import AbstractRunner
from kedro.config import AbstractConfigLoader


class ConfigurableRunner(AbstractRunner):
    """Abstract class for runners to be instantiated from a config loader"""

    @classmethod
    def from_conf_loader(
        cls, config_loader: AbstractConfigLoader, **kwargs
    ) -> AbstractRunner:
        raise NotImplementedError


def instantiate_runner(runner, config_loader) -> AbstractRunner:
    module, class_name = runner.rsplit(".", 1)

    module = import_module(module)
    runner_cls = getattr(module, class_name)

    logger.info("Using runner " + str(runner_cls))
    
    if not isinstance(runner_cls, ConfigurableRunner):
        return runner_cls()
    else:
        try:
            return runner_cls.from_conf_loader(config_loader)
        except Exception as e:
            raise ValueError(
                f"Failed to instantiate runner {runner_cls} using config loader"
            ) from e
