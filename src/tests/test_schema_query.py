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
