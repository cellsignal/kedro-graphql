import pytest

from kedro_graphql.models import ExtensionMetadata, Pipeline
from kedro_graphql.schema import decode_cursor, encode_cursor


class TestSchemaQuery:

    @pytest.mark.asyncio
    async def test_pipeline(self, mock_app, mock_info_context, mock_pipeline):

        query = """
        query TestQuery($id: String!) {
          readPipeline(id: $id){
            id
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(query, variable_values={"id": str(mock_pipeline.id)})
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_status_metadata(self, mock_app, mock_info_context, mock_pipeline):
        mock_pipeline.current_status.metadata = [
            ExtensionMetadata(key="x-runner-id", value="external-id")
        ]
        await mock_app.state.services.backend.update(mock_pipeline)
        query = """
        query TestQuery($id: String!) {
          readPipeline(id: $id) {
            name
            status { state metadata { key value } }
          }
        }
        """

        response = await mock_app.state.services.schema.execute(
            query, variable_values={"id": str(mock_pipeline.id)}
        )

        assert response.errors is None
        decoded = Pipeline.from_dict(response.data["readPipeline"])
        assert decoded.current_status.metadata == mock_pipeline.current_status.metadata

    @pytest.mark.asyncio
    async def test_pipelines(self, mock_app, mock_info_context, mock_pipeline):

        query = """
        query TestQuery($limit: Int!, $filter: String!) {
          readPipelines(limit: $limit, filter: $filter) {
            pageMeta {
              nextCursor
            }
            pipelines {
              id
            }
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(query, variable_values={"limit": 3, "filter": "{\"tags\": {\"key\": \"author\", \"value\": \"opensean\"}}"})
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_templates(self, mock_app, mock_info_context):

        query = """
        query TestQuery($limit: Int!) {
          pipelineTemplates(limit: $limit) {
            pageMeta {
              nextCursor
            }
            pipelineTemplates {
              name
              describe
              inputs {
                name
              }
              nodes {
                name
                inputs
                outputs
                tags
              }
              outputs {
                name
              }
              parameters {
                name
                value
              }
            }
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(query, variable_values={"limit": 5})

        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_template(self, mock_app, mock_info_context):
        list_query = """
        query TestQuery($limit: Int!) {
          pipelineTemplates(limit: $limit) {
            pipelineTemplates {
              id
              name
            }
          }
        }
        """
        list_resp = await mock_app.state.services.schema.execute(list_query, variable_values={"limit": 1})
        assert list_resp.errors is None
        template = list_resp.data["pipelineTemplates"]["pipelineTemplates"][0]

        query = """
        query TestQuery($id: String!) {
          pipelineTemplate(id: $id) {
            id
            name
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(query, variable_values={"id": template["id"]})
        assert resp.errors is None
        assert resp.data["pipelineTemplate"]["id"] == template["id"]
        assert resp.data["pipelineTemplate"]["name"] == template["name"]

    @pytest.mark.asyncio
    async def test_pipeline_template_ids_and_pagination(self, mock_app, mock_info_context):
        query = """
        query TestQuery($limit: Int!, $cursor: String) {
          pipelineTemplates(limit: $limit, cursor: $cursor) {
            pageMeta { nextCursor }
            pipelineTemplates { id name }
          }
        }
        """
        expected = [template.name for template in mock_app.state.services.metadata.templates]
        found = []
        cursor = None

        while True:
            resp = await mock_app.state.services.schema.execute(
                query, variable_values={"limit": 1, "cursor": cursor}
            )
            assert resp.errors is None
            page = resp.data["pipelineTemplates"]
            found.extend(page["pipelineTemplates"])
            cursor = page["pageMeta"]["nextCursor"]
            if cursor is None:
                break

        assert found == [{"id": name, "name": name} for name in expected]

    def test_cursor_round_trip_supports_unicode_and_delimiters(self):
        ids = ["pipeline:β", "66b8df706d718a4ee2a0144b"]

        assert [decode_cursor(encode_cursor(id)) for id in ids] == ids

    @pytest.mark.asyncio
    async def test_read_datasets(self, mock_app, mock_info_context, mock_pipeline):

        query = """
        query TestQuery($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
          readDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec){
            __typename
            ... on DataSet {
              name
              partitions
            }
            ... on SignedUrl {
              url
              file
              fields {
                name
                value
              }
            }
            ... on SignedUrls {
              urls {
                url
                file
                fields {
                  name
                  value
                }
              }
            }
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(
            query,
            variable_values={
                "id": str(mock_pipeline.id),
                "datasets": [
                    {"name": "text_in"},
                    {"name": "text_out"}
                ],
                "expires_in_sec": 3600
            }
        )
        assert resp.data["readDatasets"] is not None
        assert len(resp.data["readDatasets"]) == 2
        assert resp.data["readDatasets"][0]["__typename"] == "SignedUrl"
        assert resp.data["readDatasets"][0].get("url", False)
        assert resp.data["readDatasets"][0].get("fields", False)
        assert resp.data["readDatasets"][0].get("file", False)
        assert resp.data["readDatasets"][1]["__typename"] == "SignedUrl"
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_read_datasets_list_partitions(self, mock_app, mock_info_context, mock_example01):

        query = """
        query TestQuery($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
          readDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec){
            __typename
            ... on DataSet {
              name
              partitions
            }
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(
            query,
            variable_values={
                "id": str(mock_example01.id),
                "datasets": [
                    {"name": "timestamped_partitioned", "listPartitions": True}
                ],
                "expires_in_sec": 3600
            }
        )
        assert resp.data["readDatasets"] is not None
        assert len(resp.data["readDatasets"]) == 1
        assert resp.data["readDatasets"][0]["__typename"] == "DataSet"
        assert resp.data["readDatasets"][0]["name"] == "timestamped_partitioned"
        assert isinstance(resp.data["readDatasets"][0]["partitions"], list)
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_read_datasets_partitions(self, mock_app, mock_info_context, mock_example01):

        query = """
        query TestQuery($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
          readDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec){
            __typename
            ... on SignedUrls {
              urls {
                url
                file
                fields {
                  name
                  value
                }
              }
            }
          }
        }
        """
        resp = await mock_app.state.services.schema.execute(
            query,
            variable_values={
                "id": str(mock_example01.id),
                "datasets": [
                    {"name": "timestamped_partitioned", "partitions": ["part_00"]}
                ],
                "expires_in_sec": 3600
            }
        )
        assert resp.data["readDatasets"] is not None
        assert len(resp.data["readDatasets"]) == 1
        assert resp.data["readDatasets"][0]["__typename"] == "SignedUrls"
        assert isinstance(resp.data["readDatasets"][0]["urls"], list)
        assert len(resp.data["readDatasets"][0]["urls"]) == 1
        assert resp.errors is None
