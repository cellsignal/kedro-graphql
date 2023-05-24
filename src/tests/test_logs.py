"""

"""
import pytest
from kedro_graphql.logs.logger import PipelineLogStream

@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestPipelineLogStream:
    @pytest.mark.asyncio
    async def test_consume(self, mock_pipeline):
        """Requires Redis to run.
        """
        task_id = mock_pipeline.task_id
        subscriber = PipelineLogStream(task_id = task_id)
        async for e in subscriber.consume():
            assert set(e.keys()) == set(["task_id", "message_id", "message", "time"])