"""

"""
import pytest
from kedro_graphql.schema import build_schema

schema = build_schema()
@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestSchemaSubscriptions:
    @pytest.mark.asyncio
    async def test_pipeline(self, mock_info_context, mock_pipeline):
        """Requires Redis to run.
        """

        query = """
    	  subscription {
          	pipeline(id:"""+ '"' + str(mock_pipeline.id) + '"' + """) {
              id
              taskId
              status
              result
              timestamp
              traceback
            }
    	  }
        """

        sub = await schema.subscribe(query)

        async for result in sub:
            assert not result.errors

    @pytest.mark.asyncio
    async def test_pipeline_logs(self, mock_info_context, mock_pipeline, mock_pipeline2):
        """Requires Redis to run.
        This test runs two pipelines simultaneously to ensure logs messages are scoped
        to the correct pipeline.
        
        """

        query = """
    	  subscription {
          	pipelineLogs(id:"""+ '"' + str(mock_pipeline.id) + '"' + """) {
              id
              message
              messageId
              taskId
              time
            }
    	  }
        """

        sub = await schema.subscribe(query)

        async for result in sub:
            #print(result)
            assert not result.errors
            assert result.data["pipelineLogs"]["id"] == str(mock_pipeline.id)
            assert result.data["pipelineLogs"]["taskId"] == str(mock_pipeline.task_id)


        query2 = """
    	  subscription {
          	pipelineLogs(id:"""+ '"' + str(mock_pipeline2.id) + '"' + """) {
              id
              message
              messageId
              taskId
              time
            }
    	  }
        """

        sub2 = await schema.subscribe(query2)

        async for result in sub2:
            #print(result)
            assert not result.errors
            assert result.data["pipelineLogs"]["id"] == str(mock_pipeline2.id)
            assert result.data["pipelineLogs"]["taskId"] == str(mock_pipeline2.task_id)