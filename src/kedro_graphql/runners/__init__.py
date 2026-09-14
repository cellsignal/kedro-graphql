import logging
from abc import ABC, abstractmethod
from importlib import import_module

from kedro_graphql.models import State

logger = logging.getLogger("kedro")


class ExternalRunnerLifecycle(ABC):
    """Operations required to manage execution outside the Celery worker."""

    @abstractmethod
    def reconcile(self) -> State | None:
        """Inspect the external execution and return a confirmed state change."""
        raise NotImplementedError

    @abstractmethod
    def terminate(self) -> None:
        """Request termination of the external execution."""
        raise NotImplementedError


def get_runner_class(runner_import_path: str):
    module, class_name = runner_import_path.rsplit(".", 1)
    module = import_module(module)
    return getattr(module, class_name)


def has_external_lifecycle(runner_import_path: str | None) -> bool:
    return bool(
        runner_import_path
        and issubclass(get_runner_class(runner_import_path), ExternalRunnerLifecycle)
    )


def init_runner(runner_import_path: str, **runner_kwargs):
    runner_cls = get_runner_class(runner_import_path)
    logger.info("using runner " + str(runner_cls))
    return runner_cls(**runner_kwargs)
