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
            tags {
              key
              value
            }
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
                                      "parameters": [{"name":"example", "value":"hello"}],
                                      "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_creds(self, mock_info_context, mock_text_in, mock_text_out):

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
            tags {
              key
              value
            }
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
                                      "inputs": [{"name": "text_in", 
                                                  "type": "text.TextDataSet", 
                                                  "filepath": str(mock_text_in),
                                                  "credentials":[{"name":"my_creds", "value": [{"name":"username", "value":"opensean"}]}],
                                                  "credentialsNested":[{"name":"my_creds", 
                                                                       "value": [{"name": "client_kwargs", 
                                                                                 "value":[{"name":"endpoint_url", 
                                                                                            "value":"http://localhost:9000"
                                                                                         }]
                                                                                }]
                                                                      }]
                                                                      
                                      }],
                                      "outputs": [{"name": "text_out", 
                                                   "type": "text.TextDataSet", 
                                                   "filepath": str(mock_text_out)}],
                                      "parameters": [{"name":"example", "value":"hello"}],
                                      "tags": [{"key": "author", "value": "opensean"},
                                               {"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None
