"""

"""


import pytest
from kedro_graphql.schema import schema
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.config import backend, backend_kwargs


## @pytest.mark.usefixtures('celery_session_app')
## @pytest.mark.usefixtures('celery_session_worker')
## class TestSchemaQuery:
## 
##     @pytest.mark.asyncio
##     async def test_pipeline(self, mock_info_context):
##        ## class App():
##        ##     print(backend_kwargs)
##        ##     backend = backend(**backend_kwargs)
## 
##        ## class Request():
##        ##     app = App()
## 
##        ## mock_context = mocker.patch("strawberry.types.Info.context").return_value({"request": Request()})
## 
##         query = """
##         query TestQuery($id: String!) {
##           pipeline(id: $id){
##             id
##           }
##         }
##         """
##         resp = await schema.execute(query, variable_values = {"id": "test"})
##         assert resp.errors is None
## 
##     @pytest.mark.asyncio
##     async def test_pipeline_templates(self):
## 
##         query = """
##         query TestQuery {
##           pipelineTemplates {
##             name
##             describe
##             inputs {
##               name
##               filepath
##               type
##             }
##             nodes {
##               name
##               inputs
##               outputs
##               tags
##             }
##             outputs {
##               filepath
##               name
##               type
##             }
##             parameters {
##               name
##               value
##             }
##           }
##         }
##         """
##         resp = await schema.execute(query)
##         
##         assert resp.errors is None

@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestSchemaMutations:
    @pytest.mark.asyncio
    async def test_pipeline(self, mock_info_context):

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
                                      "inputs": [{"name": "text_in", "type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}],
                                      "outputs": [{"name": "text_out", "type": "text.TextDataSet", "filepath": "../data/02_intermediate/text_out.txt"}],
                                      "parameters": [{"name":"example", "value":"hello"}] 
                                    }})
        
        assert resp.errors is None

##@pytest.mark.usefixtures('celery_session_app')
##@pytest.mark.usefixtures('celery_session_worker')
##class TestSchemaSubscriptions:
##    @pytest.mark.asyncio
##    async def test_pipeline(self, celery_session_app):
##        """
##        Requires Redis to run.
##        """
##        inputs = {"text_in":{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}}
##        outputs = {"text_out":{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}}
##
##        pipeline = run_pipeline.apply_async(kwargs = {"name": "example00", "inputs": inputs, "outputs": outputs}, countdown=1) ## delay execution of task by 1 second so we dont miss all the events
##        
##        query = """
##    	  subscription {
##          	pipeline(id:"""+ '"' + pipeline.id + '"' + """)
##    	  }
##        """
##
##        sub = await schema.subscribe(query)
##
##        async for result in sub:
##            print(result)
##            ##assert not result.errors
##            ##assert result.data == {"count": index}