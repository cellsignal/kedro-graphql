"""

"""
import pytest


class TestSchemaQuery:

    @pytest.mark.asyncio
    async def test_pipeline(self, mock_app, mock_info_context, mock_pipeline):

        query = """
        query TestQuery($id: String!) {
          pipeline(id: $id){
            id
          }
        }
        """
        resp = await mock_app.schema.execute(query, variable_values = {"id": str(mock_pipeline.id)})
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_templates(self, mock_app, mock_info_context):

        query = """
        query TestQuery {
          pipelineTemplates {
            name
            describe
            inputs {
              name
              filepath
              type
            }
            nodes {
              name
              inputs
              outputs
              tags
            }
            outputs {
              filepath
              name
              type
            }
            parameters {
              name
              value
            }
          }
        }
        """
        resp = await mock_app.schema.execute(query)
        
        assert resp.errors is None
