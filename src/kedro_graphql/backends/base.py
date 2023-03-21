import abc
from kedro_graphql.models import Pipeline
import uuid

class BaseBackend(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def startup(self, **kwargs):
        """Startup hook."""
        raise NotImplementedError

    @abc.abstractmethod
    def shutdown(self, **kwargs):
        """Shutdown hook."""
        raise NotImplementedError

    @abc.abstractmethod
    def load(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id"""
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, id: uuid.UUID = None, task_id: str = None, values: dict = None):
        """Update a pipeline"""
        raise NotImplementedError