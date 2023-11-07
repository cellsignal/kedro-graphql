"""

"""


import pytest

class TestSchemaMutations:
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

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        resp = await mock_app.schema.execute(self.mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", "type": "text.TextDataSet", "filepath": str(mock_text_in)}],
                                      "outputs": [{"name": "text_out", "type": "text.TextDataSet", "filepath": str(mock_text_out)}],
                                      "parameters": [{"name":"example", "value":"hello"},
                                                     {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                      "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_creds(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        mutation = """
        mutation TestMutation($pipeline: PipelineInput!) {
          pipeline(pipeline: $pipeline) {
            id
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

        resp = await mock_app.schema.execute(mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", 
                                                  "type": "text.TextDataSet", 
                                                  "filepath": str(mock_text_in),
                                                  "credentials": "my_creds"
                                      }],
                                      "outputs": [{"name": "text_out", 
                                                   "type": "text.TextDataSet", 
                                                   "filepath": str(mock_text_out)}],
                                      "parameters": [{"name":"example", "value":"hello"}],
                                      "tags": [{"key": "author", "value": "opensean"},
                                               {"key":"package", "value":"kedro-graphql"}],

                                      "credentials":[{"name":"my_creds", 
                                                      "value": [
                                                          {"name":"key", "value":"admin"},
                                                          {"name": "secret", "value":"password"}
                                                      ]}],
                                      "credentialsNested":[{"name":"my_creds", 
                                                           "value": [{"name": "client_kwargs", 
                                                                     "value":[{"name":"endpoint_url", 
                                                                                "value":"http://localhost:9000"
                                                                             }]
                                                                    }]
                                                          }]
                                    }})
        
  
        assert resp.errors is None

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline2(self, mock_app, mock_info_context, mock_text_in_tsv, mock_text_out_tsv):

        resp = await mock_app.schema.execute(self.mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", 
                                                  "type": "pandas.CSVDataSet", 
                                                  "filepath": str(mock_text_in_tsv),
                                                  "loadArgs":[
                                                      {"name": "sep", "value": "\t"}
                                                  ],
                                                  "saveArgs":[
                                                      {"name": "sep", "value": "\t"}
                                                  ]
                                                }],
                                      "outputs": [{"name": "text_out", 
                                                   "type": "pandas.CSVDataSet", 
                                                   "filepath": str(mock_text_out_tsv),
                                                   "loadArgs":[
                                                      {"name": "sep", "value": "\t"}
                                                  ],
                                                  "saveArgs":[
                                                      {"name": "sep", "value": "\t"}
                                                  ]}],
                                      "parameters": [{"name":"example", "value":"hello"}],
                                      "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None

