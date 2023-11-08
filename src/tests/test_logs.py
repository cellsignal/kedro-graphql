"""

"""
import pytest
from kedro_graphql.logs.logger import PipelineLogStream

@pytest.mark.usefixtures('mock_celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('depends_on_current_app')
class TestPipelineLogStream:
    @pytest.mark.asyncio
    async def test_consume(self, mock_app, mock_pipeline):
        """Requires Redis to run.
        """
        task_id = mock_pipeline.task_id
        subscriber = await PipelineLogStream().create(task_id=task_id, broker_url = mock_app.config["KEDRO_GRAPHQL_BROKER"])
        async for e in subscriber.consume():
            assert set(e.keys()) == set(["task_id", "message_id", "message", "time"])