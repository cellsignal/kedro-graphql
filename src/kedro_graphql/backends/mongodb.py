import ast
import asyncio
import json
import os
import threading
import uuid
import weakref

from bson.objectid import ObjectId
from pymongo import AsyncMongoClient

from kedro_graphql.logs.logger import logger
from kedro_graphql.models import Pipeline

from .base import BaseBackend


class MongoBackend(BaseBackend):
    """MongoDB backend built on PyMongo's native async API (``AsyncMongoClient``).

    All database operations are coroutines, so resolvers can ``await`` them directly
    without delegating blocking I/O to a thread pool. An ``AsyncMongoClient`` is not
    thread safe and may only be used by a single event loop, so one client is created
    and cached per running event loop. Clients are also keyed by process id so the
    backend remains safe across ``fork`` (e.g. Celery's prefork worker pool).
    """

    def __init__(self, uri=None, db=None, collection="pipelines"):
        self.uri = uri
        self.db_name = db
        self.collection = collection
        self._pid = os.getpid()
        # Map the running event loop to its own AsyncMongoClient. Weak keys allow
        # clients to be garbage collected once their event loop is gone.
        self._clients: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncMongoClient]" = (
            weakref.WeakKeyDictionary()
        )
        self._clients_lock = threading.Lock()

    def _get_client(self) -> AsyncMongoClient:
        """Return an ``AsyncMongoClient`` bound to the current running event loop."""
        loop = asyncio.get_running_loop()
        pid = os.getpid()
        with self._clients_lock:
            if pid != self._pid:
                # Process was forked; clients are bound to the parent's event loops
                # and must not be reused.
                self._clients = weakref.WeakKeyDictionary()
                self._pid = pid
            client = self._clients.get(loop)
            if client is None:
                client = AsyncMongoClient(self.uri)
                self._clients[loop] = client
            return client

    def _get_collection(self):
        """Return the configured collection bound to the current event loop."""
        return self._get_client()[self.db_name][self.collection]

    async def startup(self, **kwargs):
        """Startup hook. Verifies connectivity and warms the connection pool."""
        await self._get_client().admin.command("ping")
        logger.info("Connected to the MongoDB database!")

    async def shutdown(self, **kwargs):
        """Shutdown hook."""
        loop = asyncio.get_running_loop()
        with self._clients_lock:
            client = self._clients.pop(loop, None)
        if client is not None:
            await client.close()

    async def list(self, cursor: uuid.UUID = None, limit=10, filter="", sort=""):
        collection = self._get_collection()

        query = {}
        if len(filter) > 0:
            filter = json.loads(filter)
            query = filter
        if cursor is not None:
            query.update({'_id': {'$gte': ObjectId(cursor)}})

        if sort:
            try:
                sort = ast.literal_eval(sort)
                # Validate that sort is a list of tuples like [('created_at', -1)]
                if isinstance(sort, list) and all(isinstance(i, tuple) and len(i) == 2 for i in sort):
                    raw = collection.find(query).sort(sort).limit(limit)
                else:
                    raise ValueError(
                        "Sort parameter should be a list of tuples like [('field', order)]")
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid sort parameter format: {e}")
        else:
            raw = collection.find(query).limit(limit)

        results = []
        async for r in raw:
            r["id"] = str(r["_id"])
            p = Pipeline.decode(r)
            results.append(p)
        return results

    async def read(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id or task_id"""
        collection = self._get_collection()

        if task_id:
            r = await collection.find_one(
                {"status": {"$elemMatch": {"task_id": task_id}}})
        else:
            r = await collection.find_one({"_id": ObjectId(id)})

        if r:
            r["id"] = str(r["_id"])
            p = Pipeline.decode(r)
            return p
        else:
            return None

    async def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        collection = self._get_collection()

        values = pipeline.encode()
        values.pop("id")  # we dont have an id yet, we will get it after insert
        created = await collection.insert_one(values)
        created = await collection.find_one({"_id": created.inserted_id})
        created["id"] = str(created["_id"])
        p = Pipeline.decode(created)
        return p

    async def update(self, pipeline: Pipeline = None):
        """Update a pipeline"""
        collection = self._get_collection()

        id = ObjectId(pipeline.id)
        filter = {'_id': id}
        values = pipeline.encode()
        values.pop("id")  # we dont want to update the id
        newvalues = {"$set": values}
        await collection.update_one(filter, newvalues)

        p = await self.read(id=id)

        return p

    async def delete(self, id: uuid.UUID = None):
        """Delete a pipeline using id"""
        collection = self._get_collection()

        await collection.delete_one({"_id": ObjectId(id)})
        return id
