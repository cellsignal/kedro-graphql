import pytest
import json
import time
IN_DEV = True


class TestSchemaMutations:
    create_pipeline_mutation = """
        mutation CreatePipeline($pipeline: PipelineInput!) {
          createPipeline(pipeline: $pipeline) {
              id
              name
              describe
              nodes {
                name
                inputs
                outputs
                tags
              }
              parameters {
                name
                value
                type
              }
              status {
                finishedAt
                state
                runner
                session
                startedAt
                taskArgs
                taskEinfo
                taskException
                taskId
                taskKwargs
                taskName
                taskRequest
                taskResult
                taskTraceback
                filteredNodes
              }
              tags {
                key
                value
              }
              parent
              createdAt
          }
        }
        """
    
    update_pipeline_mutation = """
        mutation UpdatePipeline($pipeline: PipelineInput!, $id: String!) {
          updatePipeline(pipeline: $pipeline, id: $id) {
            id
            name
            describe
            nodes {
              name
              inputs
              outputs
              tags
            }
            parameters {
              name
              value
              type
            }
            status {
              finishedAt
              state
              runner
              session
              startedAt
              taskArgs
              taskEinfo
              taskException
              taskId
              taskKwargs
              taskName
              taskRequest
              taskResult
              taskTraceback
              filteredNodes
            }
            tags {
              key
              value
            }
            parent
            createdAt
          }
        }
        """

    
    delete_pipeline_mutation = """
        mutation TestMutation($id: String!) {
          deletePipeline(id: $id) {
           id
            name
            describe
            nodes {
              name
              inputs
              outputs
              tags
            }
            parameters {
              name
              value
              type
            }
            status {
              finishedAt
              state
              runner
              session
              startedAt
              taskArgs
              taskEinfo
              taskException
              taskId
              taskKwargs
              taskName
              taskRequest
              taskResult
              taskTraceback
              filteredNodes
            }
            tags {
              key
              value
            }
            parent
            createdAt
          }
        }
        """

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        resp = await mock_app.schema.execute(self.create_pipeline_mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", "type": "text.TextDataset", "filepath": str(mock_text_in)}],
                                      "outputs": [{"name": "text_out", "type": "text.TextDataset", "filepath": str(mock_text_out)}],
                                      "parameters": [{"name":"example", "value":"hello"},
                                                     {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                      "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None

    @pytest.mark.skipif(IN_DEV, reason="credential support in development")
    @pytest.mark.asyncio
    async def test_pipeline_creds(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        resp = await mock_app.schema.execute(self.create_pipeline_mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", 
                                                  "type": "text.TextDataset", 
                                                  "filepath": str(mock_text_in),
                                                  "credentials": "my_creds"
                                      }],
                                      "outputs": [{"name": "text_out", 
                                                   "type": "text.TextDataset", 
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

        resp = await mock_app.schema.execute(self.create_pipeline_mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "inputs": [{"name": "text_in", 
                                                  "type": "pandas.CSVDataset", 
                                                  "filepath": str(mock_text_in_tsv),
                                                  "loadArgs":[
                                                      {"name": "sep", "value": "\t"}
                                                  ],
                                                  "saveArgs":[
                                                      {"name": "sep", "value": "\t"}
                                                  ]
                                                }],
                                      "outputs": [{"name": "text_out", 
                                                   "type": "pandas.CSVDataset", 
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


    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_with_config(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}
        resp = await mock_app.schema.execute(self.create_pipeline_mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
  
                                      "inputs": [{"name": "text_in", "config": json.dumps(input_dict)}],
                                      "outputs": [{"name": "text_out", "config": json.dumps(output_dict)}],
                                      "parameters": [{"name":"example", "value":"hello"},
                                                     {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                      "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_with_data_catalog(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}
        resp = await mock_app.schema.execute(self.create_pipeline_mutation, 
                                    variable_values = {"pipeline": {
                                      "name": "example00",
                                      "dataCatalog":[{"name": "text_in", "config": json.dumps(input_dict)},
                                                      {"name": "text_out", "config": json.dumps(output_dict)}],
                                      "parameters": [{"name":"example", "value":"hello"},
                                                     {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                      "tags": [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
                                    }})
        
        assert resp.errors is None

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_create_staged_pipeline(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}
        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                                                                                 {"name": "text_out", "config": json.dumps(output_dict)}],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "STAGED",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_state = create_pipeline_resp.data["createPipeline"]["status"][-1]["state"]

        assert create_pipeline_resp.errors is None
        assert pipeline_state == "STAGED"

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_create_valid_ready_pipeline(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}
        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                                                                                 {"name": "text_out", "config": json.dumps(output_dict)}],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_state = create_pipeline_resp.data["createPipeline"]["status"][-1]["state"]

        assert create_pipeline_resp.errors is None
        assert pipeline_state != "STAGED"

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_create_invalid_name_ready_pipeline(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}
        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example02",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                                                                                 {"name": "text_out", "config": json.dumps(output_dict)}],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        assert create_pipeline_resp.errors is not None

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_update_pipeline_staged_to_ready(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                                                                                 {"name": "text_out", "config": json.dumps(output_dict)}],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "STAGED",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_id = create_pipeline_resp.data["createPipeline"]["id"]

        update_pipeline_resp = await mock_app.schema.execute(self.update_pipeline_mutation,
                                                             variable_values={"id": pipeline_id,
                                                                              "pipeline": {
                                                                                  "name": "example00",
                                                                                  "state": "READY",
                                                                              }
                                                                              })
        assert update_pipeline_resp.errors is None
        pipeline_state = update_pipeline_resp.data["updatePipeline"]["status"][-1]["state"]
        assert pipeline_state != "STAGED"

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_delete_pipeline(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                                                                                 {"name": "text_out", "config": json.dumps(output_dict)}],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_id = create_pipeline_resp.data["createPipeline"]["id"]

        delete_pipeline_resp = await mock_app.schema.execute(self.delete_pipeline_mutation,
                                                             variable_values={"id": pipeline_id})

        assert delete_pipeline_resp.errors is None

    @pytest.mark.usefixtures('mock_celery_session_app')
    @pytest.mark.usefixtures('celery_session_worker')
    @pytest.mark.usefixtures('depends_on_current_app')
    @pytest.mark.asyncio
    async def test_pipeline_data_catalog_modified_with_log_datasets(self, mock_app, mock_info_context, mock_text_in, mock_text_out):

        input_dict = {"type": "text.TextDataset", "filepath": str(mock_text_in)}
        output_dict = {"type": "text.TextDataset", "filepath": str(mock_text_out)}

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                                                                                 {"name": "text_out", "config": json.dumps(output_dict)}],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                  "state": "READY",

                                                             }})
        # Sleep for 1 second to ensure pipeline before_start handler has run
        time.sleep(1)

        dataset_names = {ds.name for ds in mock_app.backend.read(create_pipeline_resp.data["createPipeline"]["id"]).data_catalog}
        
        assert "gql_meta" in dataset_names
        assert "gql_logs" in dataset_names
