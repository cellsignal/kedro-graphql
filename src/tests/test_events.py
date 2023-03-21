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



@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('celery_includes')
class TestPipelineEventMonitor:
    @pytest.mark.asyncio
    async def test_consume(self, celery_session_app):
        """
        Requires Redis to run.
        """
        inputs = {"text_in":{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}}
        outputs = {"text_out":{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}}

        result = run_pipeline.apply_async(kwargs = {"name": "example00", "inputs": inputs, "outputs": outputs}, countdown=1) ## delay execution of task by 1 second so we dont miss all the events
        async for e in PipelineEventMonitor(app = celery_session_app, uuid = result.id).consume():
            print(e)
            assert e["status"] in ALL_STATES
        
        ## try with shorter timeout to test Exception handling
        result = run_pipeline.apply_async(kwargs = {"name": "example00", "inputs": inputs, "outputs": outputs}, countdown=1) ## delay execution of task by 1 second so we dont miss all the events
        async for e in PipelineEventMonitor(app = celery_session_app, uuid = result.id, timeout = 0.01).consume():
            assert e["status"] in ALL_STATES
 
        ## let task finish before starting monitor test Exception handling
        result = run_pipeline.apply_async(kwargs = {"name": "example00", "inputs": inputs, "outputs": outputs})
        result.wait()
        async for e in PipelineEventMonitor(app = celery_session_app, uuid = result.id, timeout = 0.01).consume():
            assert e["status"] in ALL_STATES
 