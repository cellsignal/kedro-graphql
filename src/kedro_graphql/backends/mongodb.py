from .base import BaseBackend
from pymongo import MongoClient
from kedro_graphql.models import Pipeline
import uuid
from bson.objectid import ObjectId
from fastapi.encoders import jsonable_encoder


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

    def load(self, id: uuid.UUID = None, task_id: str = None):
        """Load a pipeline by id or task_id"""
        if task_id:
            r = self.db["pipelines"].find_one({"task_id": task_id})
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
            filter = {'task_id': task_id }
        else:
            filter = {'_id': ObjectId(id)}

        newvalues = { "$set": values }
        self.db["pipelines"].update_one(filter, newvalues)

        if task_id:
            p = self.load(task_id = task_id)
        else:
            p = self.load(id = id)

        return p