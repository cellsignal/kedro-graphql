import json
import pytest
from kedro_graphql.client import PIPELINE_GQL
from kedro_graphql.models import Pipeline
from pathlib import Path


class TestSchemaExtensions:

    @pytest.mark.asyncio
    async def test_pipeline_extension(self,
                                      mocker,
                                      mock_app,
                                      mock_info_context,
                                      mock_pipeline):
        """
        Test that the kedro_graphql.schema.PipelineExtension correctly masks filepaths in the pipeline's data catalog.
        """
        # parse filepath prefix from mock_pipeline datasets
        c = json.loads(mock_pipeline.data_catalog[0].config)
        prefix = "/" + c["filepath"].split("/", 2)[1] + "/"

        mocker.patch.dict("kedro_graphql.schema.CONFIG", {"KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS": [
            {"prefix": prefix, "mask": "/REDACTED/"}]})

        query = """
                    query readPipeline($id: String!) {
                      readPipeline(id: $id) """ + PIPELINE_GQL + """
                    }
                """

        resp = await mock_app.schema.execute(query, variable_values={"id": str(mock_pipeline.id)})
        assert resp.errors is None
        p = Pipeline.decode(resp.data["readPipeline"], decoder="graphql")
        for d in p.data_catalog:
            c = json.loads(d.config)
            if c.get("filepath"):
                assert not c["filepath"].startswith(prefix)
                assert c["filepath"].startswith("/REDACTED/")

    @pytest.mark.asyncio
    async def test_pipeline_input_extension_00(self,
                                               mocker,
                                               mock_app,
                                               mock_info_context,
                                               mock_text_in,
                                               mock_text_out):
        """
        Test that the kedro_graphql.schema.PipelineInputExtension correctly validates filepaths in the
        pipeline's data catalog against allowed roots.
        """

        mocker.patch.dict("kedro_graphql.schema.CONFIG", {
                          "KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS": ["./data/"], })

        query = """
            mutation createPipeline($pipeline: PipelineInput!, $uniquePaths: [String!]) {
              createPipeline(pipeline: $pipeline, uniquePaths: $uniquePaths) """ + PIPELINE_GQL + """
            }
        """
        resp = await mock_app.schema.execute(query,
                                             variable_values={"pipeline": {
                                                 "name": "example00",
                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                 {"name": "text_out", "config": json.dumps(
                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                 ],
                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                             },
                                                 "uniquePaths": ["text_in", "text_out"]})

        assert resp.errors is not None
        assert "not allowed" in resp.errors[0].message

    @pytest.mark.asyncio
    async def test_pipeline_input_extension_01(self,
                                               mocker,
                                               mock_app,
                                               mock_info_context,
                                               mock_text_in,
                                               mock_text_out):
        """
        Test that the kedro_graphql.schema.PipelineInputExtension correctly unmasks the input Dataset filepaths in the
        pipeline's data catalog and validates against allowed roots.  Check to make sure pipeline is created in the 
        backend with unmasked filepaths.
        """
        prefix = "/" + str(mock_text_in).split("/", 2)[1] + "/"
        mocker.patch.dict("kedro_graphql.schema.CONFIG", {
                          "KEDRO_GRAPHQL_DATASET_FILEPATH_ALLOWED_ROOTS": [prefix], })

        mocker.patch.dict("kedro_graphql.schema.CONFIG", {"KEDRO_GRAPHQL_DATASET_FILEPATH_MASKS": [
            {"prefix": prefix, "mask": "/REDACTED/"}]})

        query = """
            mutation createPipeline($pipeline: PipelineInput!, $uniquePaths: [String!]) {
              createPipeline(pipeline: $pipeline, uniquePaths: $uniquePaths) """ + PIPELINE_GQL + """
            }
        """
        resp = await mock_app.schema.execute(query,
                                             variable_values={"pipeline": {
                                                 "name": "example00",
                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in).replace("/tmp/", "/REDACTED/")})},
                                                                 {"name": "text_out", "config": json.dumps(
                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out).replace("/tmp/", "/REDACTED/")})}
                                                                 ],
                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                             },
                                                 "uniquePaths": ["text_in", "text_out"]})

        assert resp.errors is None

        # check response to make sure filepaths are masked
        p = Pipeline.decode(resp.data["createPipeline"], decoder="graphql")
        for d in p.data_catalog:
            c = json.loads(d.config)
            if c.get("filepath"):
                assert c["filepath"].startswith("/REDACTED/")
                assert not c["filepath"].startswith(prefix)

        # check backend to make sure filepaths are unmasked
        pipeline = mock_app.backend.read(id=p.id)
        for d in pipeline.data_catalog:
            c = json.loads(d.config)
            if c.get("filepath"):
                assert c["filepath"].startswith(prefix)
                assert not c["filepath"].startswith("/REDACTED/")
