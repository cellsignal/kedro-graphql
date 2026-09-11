import json
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from cloudevents.http import CloudEvent
from kedro.runner import SequentialRunner

from kedro_graphql.exceptions import InvalidPipeline
from kedro_graphql.models import (
    ParameterType,
    Pipeline,
    PipelineInput,
    PipelineStatus,
    State,
)
from kedro_graphql.pipeline_service import (
    abort_pipeline,
    create_pipeline,
    delete_pipeline,
    read_pipeline,
    submit_event_pipeline,
    update_pipeline,
)
from kedro_graphql.project import ProjectMetadata, load_project_metadata
from kedro_graphql.runners import ExternalRunnerLifecycle


class FakeExternalRunner(ExternalRunnerLifecycle, SequentialRunner):
    reconciled_state = None
    calls = []

    def reconcile(self):
        self.calls.append(("reconcile", self.run_context.copy()))
        return self.reconciled_state

    def terminate(self):
        self.calls.append(("terminate", self.run_context.copy()))
        self.emit_metadata({"x-external-termination": "requested"})


def _services(mock_app, backend):
    current = mock_app.state.services
    return SimpleNamespace(
        config=current.config,
        metadata=current.metadata,
        backend=backend,
        celery=current.celery,
        available_hooks=current.available_hooks,
    )


def _backend(pipeline_id="000000000000000000000001"):
    async def create(pipeline):
        pipeline.id = pipeline_id
        return pipeline

    async def update(pipeline):
        return pipeline

    async def update_if_current(pipeline, expected_state, status_count):
        return pipeline

    return SimpleNamespace(
        create=AsyncMock(side_effect=create),
        update=AsyncMock(side_effect=update),
        update_if_current=AsyncMock(side_effect=update_if_current),
        read=AsyncMock(),
        delete=AsyncMock(),
    )


def _pipeline_input(state):
    return PipelineInput.from_dict(
        {
            "name": "example00",
            "state": state,
            "data_catalog": [
                {
                    "name": "text_in",
                    "config": json.dumps(
                        {"type": "text.TextDataset", "filepath": "/tmp/in.txt"}
                    ),
                },
                {
                    "name": "text_out",
                    "config": json.dumps(
                        {"type": "text.TextDataset", "filepath": "/tmp/out.txt"}
                    ),
                },
            ],
            "parameters": [
                {"name": "example", "value": "hello"},
                {"name": "runner_kwargs.is_async", "value": "true", "type": "BOOLEAN"},
            ],
        }
    )


def _staged_pipeline():
    return Pipeline(
        id="000000000000000000000001",
        name="example00",
        status=[PipelineStatus(state=State.STAGED)],
    )


def _external_pipeline(state=State.STARTED):
    return Pipeline(
        id="000000000000000000000001",
        name="example00",
        status=[
            PipelineStatus(
                state=state,
                runner="tests.test_pipeline_service.FakeExternalRunner",
                task_id="task-id",
                metadata=[{"key": "x-external-id", "value": "execution-id"}],
            )
        ],
    )


def _runtime_config(tmp_path, catalog, parameters="", globals=""):
    source = tmp_path / "runtime-config"
    base = source / "base"
    base.mkdir(parents=True)
    (base / "catalog.yml").write_text(catalog)
    (base / "parameters.yml").write_text(parameters)
    (base / "globals.yml").write_text(globals)
    return source


@pytest.mark.asyncio
async def test_create_pipeline_service_stages_without_submission(mock_app):
    backend = _backend()
    services = _services(mock_app, backend)

    with patch("kedro_graphql.pipeline_service.run_pipeline.apply_async") as publish:
        created = await create_pipeline(
            services,
            _pipeline_input("STAGED"),
            {"email": "user@example.com"},
        )

    assert created.current_status.state is State.STAGED
    assert created.created_at is not None
    assert created.created_at.tzinfo is timezone.utc
    assert all(dataset.tags is not None for dataset in created.data_catalog)
    backend.create.assert_awaited_once()
    backend.update.assert_not_awaited()
    publish.assert_not_called()


@pytest.mark.asyncio
async def test_create_pipeline_persists_task_id_before_publication(mock_app):
    backend = _backend()
    services = _services(mock_app, backend)

    with (
        patch("kedro_graphql.pipeline_service.uuid4", return_value="task-id"),
        patch("kedro_graphql.pipeline_service.run_pipeline.apply_async") as publish,
    ):
        created = await create_pipeline(services, _pipeline_input("READY"), None)

    persisted = backend.create.await_args.args[0]
    assert persisted.current_status.task_id == "task-id"
    assert created.current_status.task_id == "task-id"
    assert publish.call_args.kwargs["task_id"] == "task-id"


@pytest.mark.asyncio
async def test_create_pipeline_records_publication_failure(mock_app):
    backend = _backend()
    services = _services(mock_app, backend)

    with (
        patch("kedro_graphql.pipeline_service.uuid4", return_value="task-id"),
        patch(
            "kedro_graphql.pipeline_service.run_pipeline.apply_async",
            side_effect=RuntimeError("broker unavailable"),
        ),
        pytest.raises(RuntimeError, match="broker unavailable"),
    ):
        await create_pipeline(services, _pipeline_input("READY"), None)

    failed, expected_state, status_count = backend.update_if_current.await_args.args
    assert expected_state is State.READY
    assert status_count == 1
    assert failed.current_status.state is State.FAILURE
    assert failed.current_status.task_id == "task-id"
    assert failed.current_status.task_exception == "broker unavailable"


@pytest.mark.asyncio
async def test_create_pipeline_resolves_runtime_config_globals_and_overrides(
    mock_app, tmp_path
):
    source = _runtime_config(
        tmp_path,
        """
text_{kind}:
  type: text.TextDataset
  filepath: ${globals:data_dir}/text_{kind}.txt
""",
        """
example: ${globals:message}
options:
  nested: default
""",
        """
data_dir: /default
message: default
""",
    )
    config = mock_app.state.services.config.model_copy(
        update={
            "env": "base",
            "pipeline_config_sources": {"example00": str(source)},
        }
    )
    backend = _backend()
    services = _services(mock_app, backend)
    services.config = config
    services.metadata = load_project_metadata(Path.cwd(), config)
    pipeline_input = PipelineInput.from_dict(
        {
            "name": "example00",
            "state": "READY",
            "globals": {"data_dir": "/request", "message": "requested"},
            "parameters": [{"name": "options.nested", "value": "overridden"}],
            "data_catalog": [
                {
                    "name": "text_in",
                    "config": json.dumps(
                        {
                            "type": "text.TextDataset",
                            "filepath": "/client/input.txt",
                        }
                    ),
                }
            ],
        }
    )

    with patch("kedro_graphql.pipeline_service.run_pipeline.apply_async"):
        created = await create_pipeline(services, pipeline_input, None)

    serial = created.to_kedro()
    assert serial["data_catalog"]["text_in"]["filepath"] == "/client/input.txt"
    assert serial["data_catalog"]["text_out"]["filepath"] == "/request/text_out.txt"
    assert serial["parameters"] == {
        "example": "requested",
        "options": {"nested": "overridden"},
    }


@pytest.mark.asyncio
async def test_slice_accepts_input_created_by_omitted_upstream_node(mock_app, tmp_path):
    source = _runtime_config(
        tmp_path,
        """
text_in:
  type: text.TextDataset
  filepath: /server/full-pipeline-input.txt
""",
    )
    config = mock_app.state.services.config.model_copy(
        update={
            "env": "base",
            "pipeline_config_sources": {"example01": str(source)},
        }
    )
    backend = _backend()
    services = _services(mock_app, backend)
    services.config = config
    services.metadata = load_project_metadata(Path.cwd(), config)
    pipeline_input = PipelineInput.from_dict(
        {
            "name": "example01",
            "state": "READY",
            "slices": [{"slice": "NODE_NAMES", "args": ["reverse_node"]}],
            "data_catalog": [
                {
                    "name": "uppercased",
                    "config": json.dumps(
                        {
                            "type": "text.TextDataset",
                            "filepath": "/client/uppercased.txt",
                        }
                    ),
                }
            ],
        }
    )

    with patch("kedro_graphql.pipeline_service.run_pipeline.apply_async"):
        created = await create_pipeline(services, pipeline_input, None)

    assert created.to_kedro()["data_catalog"] == {
        "uppercased": {
            "type": "text.TextDataset",
            "filepath": "/client/uppercased.txt",
        }
    }


@pytest.mark.asyncio
async def test_submission_rejects_unresolved_runtime_globals(mock_app, tmp_path):
    source = _runtime_config(
        tmp_path,
        """
text_in:
  type: text.TextDataset
  filepath: ${globals:missing}
""",
    )
    services = _services(mock_app, _backend())
    services.metadata = ProjectMetadata(
        pipelines={"example00": services.metadata.pipelines["example00"]},
        config_sources={"example00": source},
        templates=(),
    )

    with pytest.raises(InvalidPipeline, match="Unable to resolve configuration"):
        await create_pipeline(
            services, PipelineInput.from_dict({"name": "example00"}), None
        )


@pytest.mark.asyncio
async def test_update_pipeline_service_persists_once_before_submission(
    mock_app,
):
    stored = _staged_pipeline()
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)

    with (
        patch("kedro_graphql.pipeline_service.uuid4", return_value="task-id"),
        patch("kedro_graphql.pipeline_service.run_pipeline.apply_async") as publish,
    ):
        updated = await update_pipeline(
            services,
            str(stored.id),
            _pipeline_input("READY"),
            {"email": "user@example.com"},
        )

    assert updated.status[-1].state is State.READY
    backend.update_if_current.assert_awaited_once()
    assert updated.current_status.task_id == "task-id"
    assert publish.call_count == 1
    assert publish.call_args.kwargs["task_id"] == "task-id"
    assert publish.call_args.kwargs["kwargs"]["parameters"] == {
        "duration": 1,
        "event": "placeholder",
        "example": "hello",
        "id": "placeholder",
        "runner_kwargs": {"is_async": True},
    }


@pytest.mark.asyncio
async def test_update_pipeline_does_not_publish_after_concurrent_change(mock_app):
    stored = _staged_pipeline()
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    backend.update_if_current.side_effect = None
    backend.update_if_current.return_value = None
    services = _services(mock_app, backend)

    with (
        patch("kedro_graphql.pipeline_service.run_pipeline.apply_async") as publish,
        pytest.raises(InvalidPipeline, match="changed while it was submitted"),
    ):
        await update_pipeline(
            services, str(stored.id), _pipeline_input("READY"), None
        )

    publish.assert_not_called()


@pytest.mark.asyncio
async def test_update_pipeline_rejects_name_change_before_side_effects(mock_app):
    stored = _staged_pipeline()
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)
    pipeline_input = _pipeline_input("READY")
    pipeline_input.name = "different"

    with (
        patch("kedro_graphql.pipeline_service.run_pipeline.apply_async") as publish,
        pytest.raises(InvalidPipeline, match="Pipeline name cannot be changed"),
    ):
        await update_pipeline(services, str(stored.id), pipeline_input, None)

    backend.update.assert_not_awaited()
    backend.update_if_current.assert_not_awaited()
    publish.assert_not_called()


@pytest.mark.asyncio
async def test_update_pipeline_refreshes_describe_and_nodes(mock_app):
    stored = _staged_pipeline()
    stored.describe = "stale"
    stored.nodes = []
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)
    template = services.metadata.pipelines[stored.name]

    updated = await update_pipeline(
        services, str(stored.id), _pipeline_input("STAGED"), None
    )

    assert updated.describe == template.describe()
    assert [
        (node.name, node.inputs, node.outputs, node.tags) for node in updated.nodes
    ] == [
        (node.name, node.inputs, node.outputs, node.tags) for node in template.nodes
    ]
    backend.update_if_current.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_pipeline_abort_reads_once(mock_app):
    stored = _staged_pipeline()
    stored.status[-1].state = State.READY
    stored.status[-1].task_id = "task-id"
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)

    with patch("kedro_graphql.pipeline_service.AbortableAsyncResult"):
        await update_pipeline(
            services, str(stored.id), _pipeline_input("ABORTED"), None
        )

    backend.read.assert_awaited_once_with(id=str(stored.id))


@pytest.mark.asyncio
async def test_abort_pipeline_service_uses_explicit_celery_service(
    mock_app,
):
    stored = _staged_pipeline()
    stored.status[-1].state = State.READY
    stored.status[-1].task_id = "task-id"
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)

    with patch("kedro_graphql.pipeline_service.AbortableAsyncResult") as result:
        aborted = await abort_pipeline(
            services,
            str(stored.id),
            {"email": "user@example.com"},
        )

    result.assert_called_once_with("task-id", app=services.celery)
    result.return_value.abort.assert_called_once_with()
    backend.update_if_current.assert_awaited_once()
    assert aborted.status[-1].state is State.ABORTING
    assert aborted.status[-1].abort_requested_at is not None


@pytest.mark.asyncio
async def test_read_pipeline_reconciles_external_execution(mock_app):
    stored = _external_pipeline()
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)
    FakeExternalRunner.calls = []
    FakeExternalRunner.reconciled_state = State.SUCCESS

    reconciled = await read_pipeline(services, str(stored.id))

    assert reconciled.current_status.state is State.SUCCESS
    operation, context = FakeExternalRunner.calls[0]
    assert operation == "reconcile"
    assert context == {
        "pipeline_id": str(stored.id),
        "task_id": "task-id",
        "metadata": {"x-external-id": "execution-id"},
    }
    backend.update_if_current.assert_awaited_once()


@pytest.mark.asyncio
async def test_abort_external_execution_remains_aborting_until_confirmed(mock_app):
    stored = _external_pipeline()
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)
    FakeExternalRunner.calls = []
    FakeExternalRunner.reconciled_state = None

    with patch("kedro_graphql.pipeline_service.AbortableAsyncResult") as result:
        aborting = await abort_pipeline(services, str(stored.id), None)

    assert aborting.current_status.state is State.ABORTING
    assert {item.key: item.value for item in aborting.current_status.metadata} == {
        "x-external-id": "execution-id",
        "x-external-termination": "requested",
    }
    assert [call[0] for call in FakeExternalRunner.calls] == [
        "terminate",
        "reconcile",
    ]
    assert backend.update_if_current.await_count == 2
    result.return_value.abort.assert_called_once_with()


@pytest.mark.asyncio
async def test_delete_external_execution_waits_for_terminal_confirmation(mock_app):
    stored = _external_pipeline(State.ABORTING)
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)
    FakeExternalRunner.calls = []
    FakeExternalRunner.reconciled_state = None

    with (
        patch("kedro_graphql.pipeline_service.AbortableAsyncResult"),
        pytest.raises(InvalidPipeline, match="termination must be confirmed"),
    ):
        await delete_pipeline(services, str(stored.id), None)

    assert stored.current_status.state is State.ABORTING
    backend.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_external_execution_after_confirmation(mock_app):
    stored = _external_pipeline(State.ABORTING)
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)
    FakeExternalRunner.calls = []
    FakeExternalRunner.reconciled_state = State.ABORTED

    deleted = await delete_pipeline(services, str(stored.id), None)

    assert deleted.current_status.state is State.ABORTED
    backend.delete.assert_awaited_once_with(id=str(stored.id))


@pytest.mark.asyncio
async def test_event_service_creates_ready_pipeline_with_typed_id(mock_app):
    backend = _backend()
    services = _services(mock_app, backend)
    event = CloudEvent(
        {
            "id": "event-id",
            "source": "example.com",
            "type": "com.example.event",
        },
        {"key": "value"},
    )

    with (
        patch("kedro_graphql.pipeline_service.uuid4", return_value="task-id"),
        patch("kedro_graphql.pipeline_service.run_pipeline.apply_async") as publish,
    ):
        created = await submit_event_pipeline(
            services,
            "event00",
            event,
            {"email": "user@example.com"},
        )

    assert [status.state for status in created.status] == [State.READY]
    assert created.current_status.task_id == "task-id"
    id_parameter = next(
        parameter for parameter in created.parameters if parameter.name == "id"
    )
    assert id_parameter.value == str(created.id)
    assert id_parameter.type is ParameterType.STRING
    assert all(dataset.tags is not None for dataset in created.data_catalog)
    backend.create.assert_awaited_once()
    backend.update.assert_awaited_once()
    assert publish.call_args.kwargs["task_id"] == "task-id"
    assert publish.call_args.kwargs["kwargs"]["parameters"]["id"] == str(created.id)
