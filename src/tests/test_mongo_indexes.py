"""Focused checks runnable with unittest without the API test fixtures."""
import json
import os
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from uuid import uuid4

from click.testing import CliRunner
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, OperationFailure

from kedro_graphql.commands import gql
from kedro_graphql.config import KedroGraphQLConfig, load_config
from kedro_graphql.mongo_indexes import index_models


class MongoIndexesTests(unittest.TestCase):
    def setUp(self):
        self.definition = {"keys": [["created_at", -1], ["_id", -1]]}
        self.config = KedroGraphQLConfig(mongo_db_collection="runs", mongo_indexes=[self.definition])

    def test_native_options_and_order(self):
        config = KedroGraphQLConfig(mongo_indexes=[{
            "collection": "datasets", "keys": [["barcode", 1], ["uri", -1]],
            "name": "barcode_uri", "unique": True,
            "partialFilterExpression": {"available": True},
            "collation": {"locale": "en", "strength": 2},
        }])
        model = index_models(config)["datasets"][0].document
        self.assertEqual(list(model["key"].items()), [("barcode", 1), ("uri", -1)])
        self.assertTrue(model["unique"])
        self.assertEqual(model["partialFilterExpression"], {"available": True})
        self.assertEqual(model["collation"]["strength"], 2)
        self.assertEqual(index_models(self.config)["runs"][0].document["name"], "created_at_-1__id_-1")
        self.assertEqual(self.config.mongo_indexes, [self.definition])

    def test_yaml_and_json_configuration(self):
        runner = CliRunner()
        with runner.isolated_filesystem(), patch.dict(os.environ, {}, clear=True):
            with open("api.yaml", "w") as stream:
                stream.write('config:\n  mongo_indexes:\n    - keys: [[uri, 1]]\n      unique: true\n')
            self.assertTrue(load_config(api_spec="api.yaml").mongo_indexes[0]["unique"])
            with patch.dict(os.environ, {"KEDRO_GRAPHQL_MONGO_INDEXES": json.dumps([self.definition])}):
                self.assertEqual(load_config().mongo_indexes, [self.definition])

    def test_invalid_definitions(self):
        for definition in ({}, {"keys": []}, {"keys": {"uri": 1}},
                           {"keys": [["", 1]]}, {"keys": [["uri", 1]], "collection": ""},
                           {"keys": [["uri", 1]], "name": 42}):
            with self.subTest(definition=definition), self.assertRaises(ValueError):
                index_models(KedroGraphQLConfig(mongo_indexes=[definition]))
        with self.assertRaises(ValueError):
            index_models(KedroGraphQLConfig(mongo_indexes=[self.definition, self.definition]))

    def invoke(self, config, *args, error=None):
        client = MagicMock()
        collection = client.__enter__.return_value.__getitem__.return_value.__getitem__.return_value
        collection.list_indexes.return_value = [{"name": "_id_", "key": {"_id": 1}}]
        collection.create_indexes.return_value = ["created_at_-1__id_-1"]
        collection.create_indexes.side_effect = error
        with patch("kedro_graphql.commands.load_config", return_value=config), patch(
            "pymongo.MongoClient", return_value=client
        ) as constructor:
            result = CliRunner().invoke(
                gql, ["--project-version", "test", "mongo-indexes", *args],
                obj=SimpleNamespace(package_name="kedro_graphql"),
            )
        return result, collection, constructor

    def test_listing_does_not_write(self):
        result, collection, _ = self.invoke(self.config)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output)["collection"], "runs")
        collection.list_indexes.assert_called_once()
        collection.create_indexes.assert_not_called()
        collection.drop_index.assert_not_called()

    def test_apply_and_empty_configuration(self):
        result, collection, _ = self.invoke(self.config, "--apply")
        self.assertEqual(result.exit_code, 0, result.output)
        collection.create_indexes.assert_called_once()
        collection.list_indexes.assert_not_called()
        result, _, constructor = self.invoke(KedroGraphQLConfig(), "--apply")
        self.assertEqual(result.exit_code, 0)
        constructor.assert_not_called()
        result, _, constructor = self.invoke(KedroGraphQLConfig(mongo_indexes=[{}]), "--apply")
        self.assertNotEqual(result.exit_code, 0)
        constructor.assert_not_called()

    def test_conflict_failure_hides_credentials(self):
        result, collection, _ = self.invoke(
            self.config, "--apply", error=OperationFailure("mongodb://user:private@host", code=85)
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("runs", result.output)
        self.assertIn("85", result.output)
        self.assertNotIn("private", result.output)
        collection.drop_index.assert_not_called()

    @unittest.skipUnless(os.environ.get("KGQL_TEST_MONGO_URI"), "requires isolated Mongo test database")
    def test_native_mongo_behaviour(self):
        with MongoClient(os.environ["KGQL_TEST_MONGO_URI"], serverSelectionTimeoutMS=10000) as client:
            database_name = "kgql_indexes_test_" + uuid4().hex
            try:
                collection = client[database_name]["datasets"]
                models = index_models(KedroGraphQLConfig(mongo_indexes=[{
                    "collection": "datasets", "keys": [["uri", 1]], "name": "uri_1", "unique": True,
                }]))["datasets"]
                collection.create_indexes(models)
                collection.create_indexes(models)
                collection.insert_one({"uri": "one"})
                with self.assertRaises(DuplicateKeyError):
                    collection.insert_one({"uri": "one"})
                conflicting = index_models(KedroGraphQLConfig(mongo_indexes=[{
                    "collection": "datasets", "keys": [["uri", 1]], "name": "uri_1",
                }]))["datasets"]
                with self.assertRaises(OperationFailure):
                    collection.create_indexes(conflicting)
                self.assertTrue(collection.index_information()["uri_1"]["unique"])
                self.assertEqual(collection.count_documents({}), 1)
            finally:
                client.drop_database(database_name)


if __name__ == "__main__":
    unittest.main()
