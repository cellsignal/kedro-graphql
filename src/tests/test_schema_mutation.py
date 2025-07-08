import json
import time

import pytest

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
              dataCatalog {
                name
                config
              }
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
            dataCatalog {
                name
                config
            }
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
            dataCatalog {
                name
                config
            }
          }
        }
        """

    @pytest.mark.asyncio
    async def test_pipeline(self,
                            mock_app,
                            mock_celery_session_app,
                            celery_session_worker,
                            mock_info_context,
                            mock_text_in,
                            mock_text_out):

        resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                             variable_values={"pipeline": {
                                                 "name": "example00",
                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                 {"name": "text_out", "config": json.dumps(
                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                 ],
                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                             }})

        assert resp.errors is None

    @pytest.mark.skipif(IN_DEV, reason="credential support in development")
    @pytest.mark.asyncio
    async def test_pipeline_creds(self,
                                  mock_app,
                                  mock_celery_worker_app,
                                  celery_session_worker,
                                  mock_info_context,
                                  mock_text_in,
                                  mock_text_out):

        resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                             variable_values={"pipeline": {
                                                 "name": "example00",
                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in), "credentials": "my_creds"})},
                                                                 {"name": "text_out", "config": json.dumps(
                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                 ],
                                                 "parameters": [{"name": "example", "value": "hello"}],
                                                 "tags": [{"key": "author", "value": "opensean"},
                                                          {"key": "package", "value": "kedro-graphql"}],
                                                 "credentials": [{"name": "my_creds",
                                                                  "value": [
                                                                      {"name": "key",
                                                                          "value": "admin"},
                                                                      {"name": "secret",
                                                                          "value": "password"}
                                                                  ]}],
                                                 "credentialsNested": [{"name": "my_creds",
                                                                        "value": [{"name": "client_kwargs",
                                                                                   "value": [{"name": "endpoint_url",
                                                                                              "value": "http://localhost:9000"
                                                                                              }]
                                                                                   }]
                                                                        }]
                                             }})

        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline2(self,
                             mock_app,
                             mock_celery_session_app,
                             celery_session_worker,
                             mock_info_context,
                             mock_text_in_tsv,
                             mock_text_out_tsv):

        resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                             variable_values={"pipeline": {
                                                 "name": "example00",
                                                 "dataCatalog": [
                                                     {"name": "text_in", "config": json.dumps({"type": "pandas.CSVDataset", "filepath": str(mock_text_in_tsv), "loadArgs": [
                                                                                              {"name": "sep", "value": "\t"}], "saveArgs": [{"name": "sep", "value": "\t"}]})},
                                                     {"name": "text_out", "config": json.dumps({"type": "pandas.CSVDataset", "filepath": str(
                                                         mock_text_out_tsv), "loadArgs": [{"name": "sep", "value": "\t"}], "saveArgs": [{"name": "sep", "value": "\t"}]})}
                                                 ],
                                                 "parameters": [{"name": "example", "value": "hello"}],
                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                             }})

        assert resp.errors is None

    @pytest.mark.asyncio
    async def test_create_staged_pipeline(self,
                                          mock_app,
                                          mock_celery_session_app,
                                          celery_session_worker,
                                          mock_info_context,
                                          mock_text_in,
                                          mock_text_out):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "text_out", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                                 ],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "STAGED",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_state = create_pipeline_resp.data["createPipeline"]["status"][-1]["state"]

        assert create_pipeline_resp.errors is None
        assert pipeline_state == "STAGED"

    @pytest.mark.asyncio
    async def test_create_valid_ready_pipeline(self,
                                               mock_app,
                                               mock_celery_session_app,
                                               celery_session_worker,
                                               mock_info_context,
                                               mock_text_in,
                                               mock_text_out):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "text_out", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                                 ],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_state = create_pipeline_resp.data["createPipeline"]["status"][-1]["state"]

        assert create_pipeline_resp.errors is None
        assert pipeline_state != "STAGED"

    @pytest.mark.asyncio
    async def test_create_invalid_name_ready_pipeline(self,
                                                      mock_app,
                                                      mock_celery_session_app,
                                                      celery_session_worker,
                                                      mock_info_context,
                                                      mock_text_in,
                                                      mock_text_out):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example02",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "text_out", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                                 ],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        assert create_pipeline_resp.errors is not None

    @pytest.mark.asyncio
    async def test_update_pipeline_staged_to_ready(self,
                                                   mock_app,
                                                   mock_celery_session_app,
                                                   celery_session_worker,
                                                   mock_info_context,
                                                   mock_text_in,
                                                   mock_text_out):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "state": "STAGED",
                                                             }})

        pipeline_id = create_pipeline_resp.data["createPipeline"]["id"]

        update_pipeline_resp = await mock_app.schema.execute(self.update_pipeline_mutation,
                                                             variable_values={"id": pipeline_id,
                                                                              "pipeline": {
                                                                                  "name": "example00",
                                                                                  "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                                  {"name": "text_out", "config": json.dumps(
                                                                                                      {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                                                  ],
                                                                                  "parameters": [{"name": "example", "value": "hello"},
                                                                                                 {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                                  "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}],
                                                                                  "state": "READY",
                                                                              }
                                                                              })
        assert update_pipeline_resp.errors is None
        assert update_pipeline_resp.data["updatePipeline"]["status"][-1]["state"] != "STAGED"
        assert update_pipeline_resp.data["updatePipeline"]["dataCatalog"][0] == {
            "name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})}
        assert update_pipeline_resp.data["updatePipeline"]["dataCatalog"][1] == {
            "name": "text_out", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_out)})}
        assert update_pipeline_resp.data["updatePipeline"]["parameters"][0] == {
            "name": "example", "value": "hello", "type": "STRING"}
        assert update_pipeline_resp.data["updatePipeline"]["parameters"][1] == {
            "name": "duration", "value": "0.1", "type": "FLOAT"}
        assert update_pipeline_resp.data["updatePipeline"]["tags"][0] == {
            "key": "author", "value": "opensean"}
        assert update_pipeline_resp.data["updatePipeline"]["tags"][1] == {
            "key": "package", "value": "kedro-graphql"}

    @pytest.mark.asyncio
    async def test_delete_pipeline(self,
                                   mock_app,
                                   mock_celery_session_app,
                                   celery_session_worker,
                                   mock_info_context,
                                   mock_text_in,
                                   mock_text_out):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "text_out", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                                 ],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "tags": [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]
                                                             }})

        pipeline_id = create_pipeline_resp.data["createPipeline"]["id"]

        delete_pipeline_resp = await mock_app.schema.execute(self.delete_pipeline_mutation,
                                                             variable_values={"id": pipeline_id})

        assert delete_pipeline_resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_data_catalog_modified_with_log_datasets(self,
                                                                    mock_app,
                                                                    mock_celery_session_app,
                                                                    celery_session_worker,
                                                                    mock_info_context,
                                                                    mock_text_in,
                                                                    mock_text_out):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example00",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "text_out", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_text_out)})}
                                                                                 ],
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",

                                                             }})

        query = """
    	  subscription {
          	pipeline(id:""" + '"' + str(create_pipeline_resp.data["createPipeline"]["id"]) + '"' + """) {
              id
              status
              result
            }
    	  }
        """
        sub = await mock_app.schema.subscribe(query)

        async for result in sub:
            assert not result.errors
            if result.data["pipeline"]["status"] == "SUCCESS":
                break
        print("RESULT:", mock_app.backend.read(
            create_pipeline_resp.data["createPipeline"]["id"]))
        dataset_names = {ds.name for ds in mock_app.backend.read(
            create_pipeline_resp.data["createPipeline"]["id"]).data_catalog}

        assert "gql_meta" in dataset_names
        assert "gql_logs" in dataset_names

    @pytest.mark.asyncio
    async def test_pipeline_slicing(self,
                                    mock_app,
                                    mock_celery_session_app,
                                    celery_session_worker,
                                    mock_info_context,
                                    mock_text_in,
                                    mock_uppercased_txt,
                                    mock_reversed_txt,
                                    mock_timestamped_txt):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example01",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "uppercased", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_uppercased_txt)})},
                                                                                 {"name": "reversed", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_reversed_txt)})},
                                                                                 {"name": "timestamped", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_timestamped_txt)})}],
                                                                 "slices": {"slice": "NODE_NAMES", "args": ["uppercase_node", "reverse_node"]},
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",
                                                             }})

        query = """
    	  subscription {
          	pipeline(id:""" + '"' + str(create_pipeline_resp.data["createPipeline"]["id"]) + '"' + """) {
              id
              status
              result
            }
    	  }
        """
        sub = await mock_app.schema.subscribe(query)

        async for result in sub:
            assert not result.errors
            if result.data["pipeline"]["status"] == "SUCCESS":
                break

        # Make sure only nodes specified in "slices" were run
        assert mock_app.backend.read(create_pipeline_resp.data["createPipeline"]
                                     ["id"]).status[-1].filtered_nodes == ["uppercase_node", "reverse_node"]
        create_pipeline_resp.errors is None

    @pytest.mark.asyncio
    async def test_pipeline_run_only_missing(self,
                                             mock_app,
                                             mock_celery_session_app,
                                             celery_session_worker,
                                             mock_info_context,
                                             mock_text_in,
                                             mock_uppercased_txt,
                                             mock_reversed_txt,
                                             mock_timestamped_txt):

        create_pipeline_resp = await mock_app.schema.execute(self.create_pipeline_mutation,
                                                             variable_values={"pipeline": {
                                                                 "name": "example01",
                                                                 "dataCatalog": [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})},
                                                                                 {"name": "uppercased", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_uppercased_txt)})},
                                                                                 {"name": "reversed", "config": json.dumps(
                                                                                     {"type": "text.TextDataset", "filepath": str(mock_reversed_txt)})},
                                                                                 {"name": "timestamped", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_timestamped_txt)})}],
                                                                 "onlyMissing": True,
                                                                 "parameters": [{"name": "example", "value": "hello"},
                                                                                {"name": "duration", "value": "0.1", "type": "FLOAT"}],
                                                                 "state": "READY",
                                                             }})
        query = """
    	  subscription {
          	pipeline(id:""" + '"' + str(create_pipeline_resp.data["createPipeline"]["id"]) + '"' + """) {
              id
              status
              result
            }
    	  }
        """
        sub = await mock_app.schema.subscribe(query)

        async for result in sub:
            assert not result.errors
            if result.data["pipeline"]["status"] == "SUCCESS":
                break

        # Make sure only timestamp_node was run because the file does not exist (did not write to it in conftest.py)
        assert mock_app.backend.read(create_pipeline_resp.data["createPipeline"]
                                     ["id"]).status[-1].filtered_nodes == ["timestamp_node"]
        create_pipeline_resp.errors is None
