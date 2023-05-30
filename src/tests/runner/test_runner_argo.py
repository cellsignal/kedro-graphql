"""

"""
import pytest
from celery.result import AsyncResult

@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestArgoWorkflowRunner:
    @pytest.mark.asyncio
    async def test_consume(self, mock_settings_env_vars, mock_pipeline_argo):
        """
        """
        ## wait for task to finish
        r = AsyncResult(mock_pipeline_argo.task_id).get()

        ## fetch result
        r = AsyncResult(mock_pipeline_argo.task_id)
        assert r.status == "SUCCESS"