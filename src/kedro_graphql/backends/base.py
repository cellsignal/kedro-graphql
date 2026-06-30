import abc
import uuid

from kedro_graphql.models import Pipeline


class BaseBackend(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def startup(self, **kwargs):
        """Startup hook."""
        raise NotImplementedError

    @abc.abstractmethod
    async def shutdown(self, **kwargs):
        """Shutdown hook."""
        raise NotImplementedError

    @abc.abstractmethod
    async def read(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id"""
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self, cursor: uuid.UUID = None, limit: int = None, filter: str = None, sort: str = None):
        """List pipelines using cursor pagination"""
        raise NotImplementedError

    @abc.abstractmethod
    async def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, pipeline: Pipeline):
        """Update a pipeline"""
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, id: uuid.UUID = None):
        """Delete a pipeline"""
        raise NotImplementedError
