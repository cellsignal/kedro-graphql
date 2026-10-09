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
from kedro_graphql.catalog_search import build_pipeline_document, pipeline_document_update, public_pipeline_document

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

        query = json.loads(filter) if filter else {}
        if not isinstance(query, dict):
            raise ValueError("Filter must be a JSON object")
        try:
            ordering = ast.literal_eval(sort) if sort else [("_id", 1)]
        except (ValueError, SyntaxError) as error:
            raise ValueError("Invalid sort parameter format") from error
        if not isinstance(ordering, list) or not ordering or not all(
            isinstance(item, tuple) and len(item) == 2
            and isinstance(item[0], str) and item[0] and not item[0].startswith("$")
            and type(item[1]) is int and item[1] in (-1, 1)
            for item in ordering
        ):
            raise ValueError("Sort must be a list of (field, 1 or -1) tuples")
        if not any(field == "_id" for field, _ in ordering):
            ordering.append(("_id", ordering[-1][1]))
        if cursor is not None:
            anchor = await collection.find_one({"_id": ObjectId(cursor)},
                                               {field: 1 for field, _ in ordering})
            if anchor is None:
                raise ValueError("Pagination cursor no longer exists; refresh the search")
            equal = []
            after = []
            for index, (field, direction) in enumerate(ordering):
                value = anchor
                for segment in field.split("."):
                    value = value.get(segment) if isinstance(value, dict) else None
                actual = {"$ifNull": [f"${field}", None]}
                expected = {"$literal": value}
                operator = "$gt" if direction == 1 else "$lt"
                # The cursor identifies the lookahead row, so include that row on the next page.
                if index == len(ordering) - 1:
                    operator = "$gte" if direction == 1 else "$lte"
                after.append({"$and": [*equal, {operator: [actual, expected]}]})
                equal.append({"$eq": [actual, expected]})
            query = {"$and": [query, {"$expr": {"$or": after}}]}
        raw = collection.find(query).sort(ordering).limit(limit)

        results = []
        async for r in raw:
            r["id"] = str(r.pop("_id"))
            p = Pipeline.from_dict(public_pipeline_document(r))
            _ = p.current_status
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
            r["id"] = str(r.pop("_id"))
            p = Pipeline.from_dict(public_pipeline_document(r))
            _ = p.current_status
            return p
        else:
            return None

    async def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        collection = self._get_collection()

        values = build_pipeline_document(pipeline)
        pipeline_id = values.pop("id", None)
        if pipeline_id is not None:
            values["_id"] = ObjectId(pipeline_id)
        created = await collection.insert_one(values)
        created = await collection.find_one({"_id": created.inserted_id})
        created["id"] = str(created.pop("_id"))
        p = Pipeline.from_dict(public_pipeline_document(created))
        return p

    async def update(self, pipeline: Pipeline = None):
        """Update a pipeline"""
        collection = self._get_collection()

        id = ObjectId(pipeline.id)
        filter = {'_id': id}
        values = build_pipeline_document(pipeline)
        values.pop("id")  # we dont want to update the id
        newvalues = pipeline_document_update(values)
        await collection.update_one(filter, newvalues)

        p = await self.read(id=id)

        return p

    async def update_if_current(self, pipeline, expected_state, status_count):
        """Reject stale lifecycle writers instead of replacing newer state."""
        collection = self._get_collection()
        values = build_pipeline_document(pipeline)
        values.pop("id")
        result = await collection.update_one(
            {
                "_id": ObjectId(pipeline.id),
                f"status.{status_count - 1}.state": expected_state.value,
                "status": {"$size": status_count},
            },
            pipeline_document_update(values),
        )
        if not result.matched_count:
            return None
        return await self.read(id=pipeline.id)

    async def delete(self, id: uuid.UUID = None):
        """Delete a pipeline using id"""
        collection = self._get_collection()

        await collection.delete_one({"_id": ObjectId(id)})
        return id
