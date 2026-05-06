import pytest


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
        resp = await mock_app.schema.execute(query, variable_values={"id": str(mock_pipeline.id)})
        assert resp.errors is None

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
        resp = await mock_app.schema.execute(query, variable_values={"limit": 3, "filter": "{\"tags\": {\"key\": \"author\", \"value\": \"opensean\"}}"})
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
        resp = await mock_app.schema.execute(query, variable_values={"limit": 5})

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
        list_resp = await mock_app.schema.execute(list_query, variable_values={"limit": 1})
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
        resp = await mock_app.schema.execute(query, variable_values={"id": template["id"]})
        assert resp.errors is None
        assert resp.data["pipelineTemplate"]["id"] == template["id"]
        assert resp.data["pipelineTemplate"]["name"] == template["name"]

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
        resp = await mock_app.schema.execute(
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
        resp = await mock_app.schema.execute(
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
        resp = await mock_app.schema.execute(
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
