"""
This module contains an example test.

Tests should be placed in ``src/tests``, in modules that mirror your
project's structure, and in files named test_*.py. They are simply functions
named ``test_*`` which test a unit of logic.

To run the tests, run ``kedro test`` from the project root directory.
"""


import pytest
from kedro_graphql.events import PipelineEventMonitor
from kedro_graphql.tasks import run_pipeline
import time
from celery.states import ALL_STATES
from celery.result import AsyncResult 



@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('celery_includes')
class TestPipelineEventMonitor:
    @pytest.mark.asyncio
    async def test_consume_default(self, mocker, celery_session_app, mock_pipeline):
        """
        Requires Redis to run.
        """
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.before_start")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_success")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_retry")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_failure")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.after_return")

        async for e in PipelineEventMonitor(app = celery_session_app, task_id = mock_pipeline.task_id).consume():
            print(e)
            assert e["status"] in ALL_STATES

    @pytest.mark.asyncio
    async def test_consume_short_timeout(self, mocker, celery_session_app, mock_pipeline):
        """
        Requires Redis to run.

        Test with shorter timeout to test Exception handling
        """
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.before_start")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_success")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_retry")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_failure")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.after_return")

        async for e in PipelineEventMonitor(app = celery_session_app, task_id = mock_pipeline.task_id, timeout = 0.01).consume():
            print(e)
            assert e["status"] in ALL_STATES
        
    @pytest.mark.asyncio
    async def test_consume_exception(self, mocker, celery_session_app, mock_pipeline):
        """
        Requires Redis to run.

        Let task finish before starting monitor test Exception handling
        """
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.before_start")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_success")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_retry")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.on_failure")
        mocker.patch("kedro_graphql.tasks.KedroGraphqlTask.after_return")

        result = AsyncResult(mock_pipeline.task_id).wait()
        async for e in PipelineEventMonitor(app = celery_session_app, task_id = mock_pipeline.task_id).consume():
            print(e)
            assert e["status"] in ALL_STATES
