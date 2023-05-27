"""

"""
import pytest

@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestArgoWorkflowRunner:
    @pytest.mark.asyncio
    async def test_consume(self, mock_env_runner_argo_workflows, mock_pipeline_s3):
        """
        """
        print(mock_env_runner_argo_workflows)