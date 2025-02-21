import abc
import uuid

from kedro_graphql.models import Pipeline


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
    def read(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id"""
        raise NotImplementedError

    @abc.abstractmethod
    def list(self, cursor: uuid.UUID = None, limit: int = None, filter: str = None, sort: str = None):
        """List pipelines using cursor pagination"""
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, pipeline: Pipeline):
        """Update a pipeline"""
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, id: uuid.UUID = None):
        """Delete a pipeline"""
        raise NotImplementedError
