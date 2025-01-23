from .base import BaseBackend
from pymongo import MongoClient
from kedro_graphql.models import Pipeline
import uuid
from bson.objectid import ObjectId
from fastapi.encoders import jsonable_encoder
import json
import ast


class MongoBackend(BaseBackend):

    def __init__(self, uri = None, db = None):
        #self.client = MongoClient(app.config["MONGO_URI"])
        self.client = MongoClient(uri)
        #self.db = self.client[app.config["MONGO_DB_NAME"]]
        self.db = self.client[db]
        #self.app = app


    def startup(self, **kwargs):
        """Startup hook."""
        print("Connected to the MongoDB database!")

    def shutdown(self, **kwargs):
        """Shutdown hook."""
        self.client.close()

    def list(self, cursor: uuid.UUID = None, limit = 10, filter = "", sort = ""):
        query = {'_id': { '$gte': ObjectId(cursor)}}
        if len(filter) > 0:
            filter = json.loads(filter)
            query.update(filter)
        
        if sort:
            try:
                sort = ast.literal_eval(sort)
                # Validate that sort is a list of tuples like [('created_at', -1)]
                if isinstance(sort, list) and all(isinstance(i, tuple) and len(i) == 2 for i in sort):
                    raw = self.db["pipelines"].find(query).sort(sort).limit(limit)
                else:
                    raise ValueError("Sort parameter should be a list of tuples like [('field', order)]")
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid sort parameter format: {e}")
        else:
            raw = self.db["pipelines"].find(query).limit(limit)

        results = []
        for r in raw:
            id = r.pop("_id")
            p = Pipeline.from_dict(r)
            p.id = str(id)
            results.append(p)
        return results

    def load(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id or task_id"""
        if task_id:
            r = self.db["pipelines"].find_one({"status": {"$elemMatch": {"task_id": task_id}}})
        else:
            r = self.db["pipelines"].find_one({"_id": ObjectId(id)})

        if r:
            id = r.pop("_id")
            p = Pipeline.from_dict(r)
            p.id = str(id)
            return p
        else:
            return None

    def create(self, pipeline: Pipeline):
        """Save a pipeline"""
        j = jsonable_encoder(pipeline)
        created = self.db["pipelines"].insert_one(j)
        created = self.db["pipelines"].find_one({"_id": created.inserted_id})
        pipeline.id = created["_id"]
        return pipeline

    def update(self, id: uuid.UUID = None, task_id: str = None, values = {}):
        """Update a pipeline using id or task id"""
        if task_id:
            filter = {"status": {"$elemMatch": {"task_id": task_id}}}
        else:
            filter = {'_id': ObjectId(id)}
        
        # Update the last object in the "status" array
        pipeline = self.db["pipelines"].find_one(filter, {'status': 1})
        last_index = len(pipeline['status']) - 1
        status_updates = {f"status.{last_index}.{key}": jsonable_encoder(value) for key, value in values.items()}
        self.db["pipelines"].update_one(filter, {"$set": status_updates})

        if task_id:
            p = self.load(task_id = task_id)
        else:
            p = self.load(id = id)

        return p