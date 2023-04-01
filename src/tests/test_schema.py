"""
This module contains an example test.

Tests should be placed in ``src/tests``, in modules that mirror your
project's structure, and in files named test_*.py. They are simply functions
named ``test_*`` which test a unit of logic.

To run the tests, run ``kedro test`` from the project root directory.
"""


import pytest
from kedro_graphql.schema import schema, Mutation, Query
from kedro_graphql.tasks import run_pipeline

#@pytest.mark.usefixtures('celery_session_app')
#@pytest.mark.usefixtures('celery_session_worker')
#class TestSchemaSubscriptions:
#    @pytest.mark.asyncio
#    async def test_pipeline(self, celery_session_app):
#        """
#        Requires Redis to run.
#        """
#        inputs = {"text_in":{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}}
#        outputs = {"text_out":{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}}
#
#        pipeline = run_pipeline.apply_async(kwargs = {"name": "example00", "inputs": inputs, "outputs": outputs}, countdown=1) ## delay execution of task by 1 second so we dont miss all the events
#        
#        query = """
#    	subscription {
#        	pipeline(uuid:"""+ '"' + pipeline.id + '"' + """)
#    	}
#        """
#
#        sub = await schema.subscribe(query)
#
#        async for result in sub:
#            print(result)
#            ##assert not result.errors
#            ##assert result.data == {"count": index}
class TestSchemaQuery:
    @pytest.mark.asyncio
    async def test_pipeline_templates(self):

        query = """
    	mutation TestMutation {
          pipeline(pipeline:{
            name: "example00"
            inputs: [{name: "text_in", type: "text.TextDataSet", filepath: "./data/01_raw/text_in.txt"}]
            outputs: [{name: "text_out", type: "text.TextDataSet", filepath: "../data/02_intermediate/text_out.txt"}]
            parameters: [{name:"example", value:"hello"}]}
          ) {
            id
            name
            inputs {
              name
              filepath
              type
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
          }
        }
        """
        resp = await schema.execute(query)
        
        assert resp.errors is None


class TestSchemaMutations:
    @pytest.mark.asyncio
    async def test_pipeline(self, mocker):

        mocker.patch("strawberry.types.Info.context")
        mutation = """
    	mutation TestMutation {
          pipeline(pipeline:{
            name: "example00"
            inputs: [{name: "text_in", type: "text.TextDataSet", filepath: "./data/01_raw/text_in.txt"}]
            outputs: [{name: "text_out", type: "text.TextDataSet", filepath: "../data/02_intermediate/text_out.txt"}]
            parameters: [{name:"example", value:"hello"}]}
          ) {
            id
            name
            inputs {
              name
              filepath
              type
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
          }
        }
        """
        resp = await schema.execute(mutation, root_value = Mutation())
        
        assert resp.errors is None
