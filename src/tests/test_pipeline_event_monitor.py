import pytest
from celery.result import AsyncResult
from celery.states import ALL_STATES

from kedro_graphql.pipeline_event_monitor import PipelineEventMonitor


class TestPipelineEventMonitor:

    @pytest.mark.asyncio
    async def test_consume_default(self, mocker, mock_app, mock_celery_session_app, mock_pipeline):
        """
        Requires Redis to run.
        """
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.before_start")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_success")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_retry")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_failure")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.after_return")

        async for e in PipelineEventMonitor(app=mock_celery_session_app, task_id=mock_pipeline.status[-1].task_id).start():
            print(e)
            assert e["status"] in ALL_STATES

    @pytest.mark.asyncio
    async def test_consume_short_timeout(self, mocker, mock_app, mock_celery_session_app, mock_pipeline):
        """
        Requires Redis to run.

        Test with shorter timeout to test Exception handling
        """
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.before_start")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_success")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_retry")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_failure")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.after_return")

        async for e in PipelineEventMonitor(app=mock_celery_session_app, task_id=mock_pipeline.status[-1].task_id, timeout=0.01).start():
            print(e)
            assert e["status"] in ALL_STATES

    @pytest.mark.asyncio
    async def test_consume_exception(self, mocker, mock_app, mock_celery_session_app, mock_pipeline):
        """
        Requires Redis to run.

        Let task finish before starting monitor test Exception handling
        """
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.before_start")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_success")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_retry")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_failure")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.after_return")

        result = AsyncResult(mock_pipeline.status[-1].task_id).wait()

        async for e in PipelineEventMonitor(app=mock_celery_session_app, task_id=mock_pipeline.status[-1].task_id).start():
            print(e)
            assert e["status"] in ALL_STATES
