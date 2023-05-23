"""

"""
import pytest
from kedro_graphql.schema import build_schema
from kedro_graphql.logs.logger import RedisLogStream

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
    async def test_pipeline_logs(self, mock_info_context, mock_pipeline):
        """Requires Redis to run.
        """

        query = """
    	  subscription {
          	pipelineLogs(id:"""+ '"' + str(mock_pipeline.id) + '"' + """) {
              id
              messageId
              message
            }
    	  }
        """

        sub = await schema.subscribe(query)

        async for result in sub:
            print(result)
            assert not result.errors
