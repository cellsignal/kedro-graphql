"""

"""


import pytest
from kedro_graphql.schema import build_schema

schema = build_schema()

@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestSchemaMutations:
    @pytest.mark.asyncio
    async def test_pipeline(self, mock_info_context, mock_text_in, mock_text_out):

        mutation = """
        mutation TestMutation($pipeline: PipelineInput!) {
          pipeline(pipeline: $pipeline) {
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
            status
            taskId
            taskName
            taskArgs
            taskKwargs
            taskRequest
            taskException
            taskTraceback
            taskEinfo
            taskResult
          }
        }
        """

        resp = await schema.execute(mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", "type": "text.TextDataSet", "filepath": str(mock_text_in)}],
                                      "outputs": [{"name": "text_out", "type": "text.TextDataSet", "filepath": str(mock_text_out)}],
                                      "parameters": [{"name":"example", "value":"hello"}] 
                                    }})
        
        assert resp.errors is None
