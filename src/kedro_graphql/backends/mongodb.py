import ast
import json
import uuid

from bson.objectid import ObjectId
from pymongo import MongoClient

from kedro_graphql.models import Pipeline

from .base import BaseBackend


class MongoBackend(BaseBackend):

    def __init__(self, uri=None, db=None, collection="pipelines"):
        self.client = MongoClient(uri)
        self.db = self.client[db]
        self.collection = collection

    def startup(self, **kwargs):
        """Startup hook."""
        print("Connected to the MongoDB database!")

    def shutdown(self, **kwargs):
        """Shutdown hook."""
        self.client.close()

    def list(self, cursor: uuid.UUID = None, limit=10, filter="", sort=""):
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
                    raw = self.db[self.collection].find(query).sort(sort).limit(limit)
                else:
                    raise ValueError(
                        "Sort parameter should be a list of tuples like [('field', order)]")
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid sort parameter format: {e}")
        else:
            raw = self.db[self.collection].find(query).limit(limit)

        results = []
        for r in raw:
            r["id"] = str(r["_id"])
            p = Pipeline.decode(r)
            results.append(p)
        return results

    def read(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id or task_id"""
        if task_id:
            r = self.db[self.collection].find_one(
                {"status": {"$elemMatch": {"task_id": task_id}}})
        else:
            r = self.db[self.collection].find_one({"_id": ObjectId(id)})

        if r:
            r["id"] = str(r["_id"])
            p = Pipeline.decode(r)
            return p
        else:
            return None

    def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        values = pipeline.encode()
        values.pop("id")  # we dont have an id yet, we will get it after insert
        created = self.db[self.collection].insert_one(values)
        created = self.db[self.collection].find_one({"_id": created.inserted_id})
        created["id"] = str(created["_id"])
        p = Pipeline.decode(created)
        return p

    def update(self, pipeline: Pipeline = None):
        """Update a pipeline"""
        id = ObjectId(pipeline.id)
        filter = {'_id': id}
        values = pipeline.encode()
        values.pop("id")  # we dont want to update the id
        newvalues = {"$set": values}
        self.db[self.collection].update_one(filter, newvalues)

        p = self.read(id=id)

        return p

    def delete(self, id: uuid.UUID = None):
        """Delete a pipeline using id"""
        self.db[self.collection].delete_one({"_id": ObjectId(id)})
        return id
