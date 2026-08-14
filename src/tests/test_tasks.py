import json
import signal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from unittest.mock import patch, MagicMock

from kedro_graphql.models import (
    DataSet,
    Parameter,
    Pipeline,
    PipelineStatus,
    State,
    Tag,
)
from kedro_graphql.tasks import (
    KedroGraphqlTask,
    _run_pipeline_in_child_process,
    run_pipeline,
)
from cloudevents.pydantic.v1 import CloudEvent
from cloudevents.conversion import to_json


@pytest.mark.asyncio
async def test_run_pipeline(mock_app,
                            mock_info_context,
                            mock_celery_session_app,
                            celery_session_worker,
                            mock_text_in,
                            mock_text_out):
    """
    This test will fail because the pipeline is missing in the backend
    """
    inputs = [{"name": "text_in", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name": "text_out", "config": json.dumps(
        {"type": "text.TextDataset", "filepath": str(mock_text_out)})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "opensean"}, {
        "key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example00",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter.from_dict(p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.STAGED,
                               runner="kedro.runner.SequentialRunner",
                               session=None,
                               started_at=None,
                               finished_at=None,
                               task_id=None,
                               task_name=None)]
    )

    p = await mock_app.state.services.backend.create(p)
    serial = p.to_kedro()

    result = run_pipeline.delay(
        id=str(p.id),
        name=serial["name"],
        data_catalog=serial["data_catalog"],
        parameters=serial["parameters"],
        runner="kedro.runner.SequentialRunner"
    )
    result = result.wait(timeout=None, interval=0.5)


def test_run_pipeline_child_process_recreates_catalog():
    """
    Verify that the child process recreates the catalog from config (dict) and parameters,
    avoiding fork-safety issues with S3.
    """

    catalog_config = {
        "text_in": {
            "type": "text.TextDataset",
            "filepath": "./data/text_in.txt"
        }
    }
    parameters = {"example": "hello"}
    
    # Mock the DataCatalog to track if from_config is called in the child
    with patch('kedro_graphql.tasks.DataCatalog') as mock_catalog_class:
        mock_catalog_instance = MagicMock()
        mock_catalog_class.from_config.return_value = mock_catalog_instance
        
        with patch('kedro_graphql.tasks.queue.Queue') as mock_queue:
            # Mock the result queue, runner, and pipeline
            result_queue = MagicMock()
            mock_runner = MagicMock()
            mock_runner.run.return_value = {"status": "success"}
            mock_pipeline = MagicMock()
            mock_hook_manager = MagicMock()
            
            _run_pipeline_in_child_process(
                runner_instance=mock_runner,
                filtered_pipeline=mock_pipeline,
                catalog_config=catalog_config,
                parameters=parameters,
                hook_manager=mock_hook_manager,
                session_id="test-session",
                record_data={},
                pipeline_name="test_pipeline",
                task_id="test-task-id",
                broker_url="redis://localhost:6379/15",
                result_queue=result_queue
            )
            
            # Verify that DataCatalog.from_config was called with the config dict
            mock_catalog_class.from_config.assert_called_once_with(catalog=catalog_config)
            
            # Verify that catalog.add_feed_dict was called to add parameters
            mock_catalog_instance.add_feed_dict.assert_called_once()
            
            # Verify the runner was called with the newly created catalog
            mock_runner.run.assert_called_once()
            call_args = mock_runner.run.call_args
            assert call_args[1]['catalog'] == mock_catalog_instance
            
            # Verify success was reported
            result_queue.put.assert_called_with((State.SUCCESS, None, None))
            mock_hook_manager.hook.after_pipeline_run.assert_called_once()
            mock_hook_manager.hook.on_pipeline_error.assert_not_called()


def test_run_pipeline_child_process_reports_abort_once():
    callbacks = {}
    result_queue = MagicMock()
    runner = MagicMock()
    hook_manager = MagicMock()

    def register(signum, callback):
        callbacks[signum] = callback

    def abort(*args, **kwargs):
        callbacks[signal.SIGTERM](signal.SIGTERM, None)

    runner.run.side_effect = abort
    with patch("kedro_graphql.tasks.signal.signal", side_effect=register), patch(
        "kedro_graphql.tasks.DataCatalog"
    ), patch("kedro_graphql.tasks.KedroGraphQLLogHandler"):
        _run_pipeline_in_child_process(
            runner,
            MagicMock(),
            {},
            {},
            hook_manager,
            "session",
            {},
            "pipeline",
            "task",
            "redis://localhost",
            result_queue,
        )

    outcome, error, trace = result_queue.put.call_args.args[0]
    assert outcome is State.ABORTED
    assert "abort signal" in error
    assert "KeyboardInterrupt" in trace
    hook_manager.hook.on_pipeline_error.assert_called_once()
    hook_manager.hook.after_pipeline_run.assert_not_called()


def test_duplicate_and_missing_callback_delivery_is_idempotent():
    pipeline = Pipeline(
        id="000000000000000000000001",
        name="example",
        status=[PipelineStatus(state=State.SUCCESS)],
    )
    backend = SimpleNamespace(
        read=AsyncMock(side_effect=[pipeline, None]),
        update_if_current=AsyncMock(),
    )
    task = KedroGraphqlTask()
    task._db = backend

    assert task._transition(str(pipeline.id), "task", State.SUCCESS) is pipeline
    assert task._transition(str(pipeline.id), "task", State.FAILURE) is None
    backend.update_if_current.assert_not_awaited()
