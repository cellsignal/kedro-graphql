import json
import signal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from unittest.mock import patch, MagicMock

from kedro_graphql.models import (
    DataSet,
    ExtensionMetadata,
    Parameter,
    Pipeline,
    PipelineStatus,
    State,
    Tag,
)
from kedro.runner import SequentialRunner
from kedro_graphql.runners import ExternalRunnerLifecycle
from kedro_graphql.tasks import (
    KedroGraphqlTask,
    _run_pipeline_in_child_process,
    run_pipeline,
)
from cloudevents.pydantic.v1 import CloudEvent
from cloudevents.conversion import to_json


class MetadataRunner(SequentialRunner):
    def run(self, *args, **kwargs):
        self.emit_metadata({"x-runner-id": "external-id"})
        return super().run(*args, **kwargs)


class FailingRunner(SequentialRunner):
    def run(self, *args, **kwargs):
        raise ValueError("child exploded")


class LifecycleRunner(ExternalRunnerLifecycle, SequentialRunner):
    def reconcile(self):
        return None

    def terminate(self):
        return None


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
                               runner="tests.test_tasks.MetadataRunner",
                               session=None,
                               started_at=None,
                               finished_at=None,
                               task_id=None,
                               task_name=None)]
    )

    p = await mock_app.state.services.backend.create(p)
    result = run_pipeline.delay(id=str(p.id))
    assert result.wait(timeout=None, interval=0.5) == "success"
    stored = await mock_app.state.services.backend.read(id=p.id)
    assert stored.current_status.metadata == [
        ExtensionMetadata(key="x-runner-id", value="external-id")
    ]


@pytest.mark.asyncio
async def test_run_pipeline_preserves_child_traceback(
    mock_app,
    mock_info_context,
    mock_celery_session_app,
    celery_session_worker,
    mock_text_in,
    mock_text_out,
):
    pipeline = Pipeline(
        name="example00",
        data_catalog=[
            DataSet(
                name="text_in",
                config=json.dumps(
                    {"type": "text.TextDataset", "filepath": str(mock_text_in)}
                ),
            ),
            DataSet(
                name="text_out",
                config=json.dumps(
                    {"type": "text.TextDataset", "filepath": str(mock_text_out)}
                ),
            ),
        ],
        parameters=[Parameter(name="example", value=json.dumps("hello"))],
        status=[
            PipelineStatus(
                state=State.STAGED,
                runner="tests.test_tasks.FailingRunner",
            )
        ],
    )
    pipeline = await mock_app.state.services.backend.create(pipeline)

    result = run_pipeline.delay(id=str(pipeline.id))

    with pytest.raises(RuntimeError) as error:
        result.wait(timeout=None, interval=0.5)
    assert "Child process traceback:" in str(error.value)
    assert "ValueError: child exploded" in str(error.value)


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
    
    # Mock process-local constructors to prove execution dependencies are not
    # supplied by the parent.
    with patch('kedro_graphql.pipeline_config.DataCatalog') as mock_catalog_class:
        mock_catalog_instance = MagicMock()
        mock_catalog_class.from_config.return_value = mock_catalog_instance

        with patch('kedro_graphql.tasks.init_runner') as init_runner, patch(
            'kedro_graphql.tasks.hook_manager_for'
        ) as hook_manager_for, patch(
            'kedro_graphql.tasks.pipelines'
        ) as pipeline_registry, patch(
            'kedro_graphql.tasks.KedroGraphQLLogHandler'
        ):
            # Mock the result queue, runner, and pipeline
            result_queue = MagicMock()
            mock_runner = MagicMock()
            mock_runner.run.return_value = {"status": "success"}
            mock_pipeline = MagicMock()
            mock_hook_manager = MagicMock()
            init_runner.return_value = mock_runner
            hook_manager_for.return_value = mock_hook_manager
            pipeline_registry.__getitem__.return_value.only_nodes.return_value = mock_pipeline

            _run_pipeline_in_child_process(
                runner="tests.test_tasks.MetadataRunner",
                runner_kwargs={"is_async": True},
                pipeline_name="test_pipeline",
                node_names=["node"],
                catalog_config=catalog_config,
                parameters=parameters,
                hook_names=["test-hook"],
                session_id="test-session",
                record_data={},
                pipeline_id="pipeline-id",
                task_id="test-task-id",
                runner_metadata={},
                broker_url="redis://localhost:6379/15",
                result_queue=result_queue
            )

            init_runner.assert_called_once_with(
                runner_import_path="tests.test_tasks.MetadataRunner", is_async=True
            )
            hook_manager_for.assert_called_once_with(["test-hook"])
            pipeline_registry.__getitem__.return_value.only_nodes.assert_called_once_with(
                "node"
            )

            # Verify that DataCatalog.from_config was called with the config dict
            mock_catalog_class.from_config.assert_called_once_with(catalog=catalog_config)
            
            # Verify that catalog.add_feed_dict was called to add parameters
            mock_catalog_instance.add_feed_dict.assert_called_once()
            
            # Verify the runner was called with the newly created catalog
            mock_runner.run.assert_called_once()
            call_args = mock_runner.run.call_args
            assert call_args[1]['catalog'] == mock_catalog_instance
            for callback in (
                mock_hook_manager.hook.after_catalog_created,
                mock_hook_manager.hook.before_pipeline_run,
                mock_hook_manager.hook.after_pipeline_run,
            ):
                assert callback.call_args.kwargs["catalog"] is mock_catalog_instance
            
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
        "kedro_graphql.tasks.init_runner", return_value=runner
    ), patch(
        "kedro_graphql.tasks.hook_manager_for", return_value=hook_manager
    ), patch(
        "kedro_graphql.tasks.pipelines"
    ) as pipeline_registry, patch("kedro_graphql.tasks.KedroGraphQLLogHandler"):
        pipeline_registry.__getitem__.return_value.only_nodes.return_value = MagicMock()
        _run_pipeline_in_child_process(
            "tests.test_tasks.MetadataRunner",
            {},
            "pipeline",
            ["node"],
            {},
            {},
            [],
            "session",
            {},
            "pipeline-id",
            "task",
            {},
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


def test_filtered_nodes_update_handles_missing_pipeline():
    backend = SimpleNamespace(
        read=AsyncMock(return_value=None),
        update_if_current=AsyncMock(),
    )
    task = KedroGraphqlTask()
    task._db = backend

    assert task._persist_filtered_nodes("missing", "task", ["node"]) is None
    backend.update_if_current.assert_not_awaited()


def test_run_pipeline_stops_when_abort_precedes_task_body():
    pipeline = Pipeline(
        id="000000000000000000000001",
        name="example",
        status=[PipelineStatus(state=State.ABORTING)],
    )
    backend = SimpleNamespace(read=AsyncMock(return_value=pipeline))

    with patch.object(run_pipeline, "_db", backend), patch(
        "kedro_graphql.tasks.create_pipeline_session"
    ) as create_session:
        assert run_pipeline.run(id=str(pipeline.id)) == "aborted"

    create_session.assert_not_called()


def test_external_runner_local_exit_does_not_confirm_abort():
    pipeline = Pipeline(
        id="000000000000000000000001",
        name="example",
        status=[
            PipelineStatus(
                state=State.ABORTING,
                runner="tests.test_tasks.LifecycleRunner",
                task_id="task-id",
            )
        ],
    )
    backend = SimpleNamespace(
        read=AsyncMock(return_value=pipeline),
        update_if_current=AsyncMock(),
    )
    task = KedroGraphqlTask()
    task._db = backend
    task._gql_config = SimpleNamespace(log_tmp_dir="/tmp")

    with patch("kedro_graphql.tasks.shutil.rmtree"):
        task.after_return(
            "SUCCESS",
            "aborted",
            "task-id",
            (),
            {"id": str(pipeline.id)},
            None,
        )

    assert pipeline.current_status.state is State.ABORTING
    backend.update_if_current.assert_not_awaited()


@pytest.mark.parametrize(
    ("runner", "expected"),
    [
        ("kedro.runner.SequentialRunner", State.ABORTED),
        ("tests.test_tasks.LifecycleRunner", State.ABORTING),
    ],
)
def test_success_callback_handles_aborted_result_by_runner_lifecycle(
    runner, expected
):
    pipeline = Pipeline(
        id="000000000000000000000001",
        name="example",
        status=[PipelineStatus(state=State.ABORTING, runner=runner, task_id="task-id")],
    )
    backend = SimpleNamespace(
        read=AsyncMock(return_value=pipeline),
        update_if_current=AsyncMock(return_value=pipeline),
    )
    task = KedroGraphqlTask()
    task._db = backend

    task.on_success("aborted", "task-id", (), {"id": str(pipeline.id)})

    assert pipeline.current_status.state is expected


def test_child_emits_runner_metadata_over_parent_queue():
    result_queue = MagicMock()
    runner = MagicMock()
    hook_manager = MagicMock()
    runner.run.side_effect = lambda *args, **kwargs: runner.emit_metadata(
        {"x-runner-id": "external-id"}
    )

    with patch(
        "kedro_graphql.tasks.init_runner", return_value=runner
    ), patch(
        "kedro_graphql.tasks.hook_manager_for", return_value=hook_manager
    ), patch(
        "kedro_graphql.tasks.pipelines"
    ) as pipeline_registry, patch("kedro_graphql.tasks.KedroGraphQLLogHandler"):
        pipeline_registry.__getitem__.return_value.only_nodes.return_value = MagicMock()
        _run_pipeline_in_child_process(
            "tests.test_tasks.MetadataRunner",
            {},
            "pipeline",
            ["node"],
            {},
            {},
            [],
            "session",
            {},
            "pipeline-id",
            "task-id",
            {"x-existing": "value"},
            "redis://localhost",
            result_queue,
        )

    assert result_queue.put.call_args_list[0].args[0] == (
        "metadata",
        {"x-runner-id": "external-id"},
    )
    assert runner.run_context == {
        "pipeline_id": "pipeline-id",
        "task_id": "task-id",
        "metadata": {"x-existing": "value"},
    }
