"""

"""
import pytest
from kedro_graphql.schema import schema
from kedro_graphql.tasks import run_pipeline

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