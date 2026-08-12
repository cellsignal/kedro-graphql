import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from cloudevents.http import CloudEvent

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
    submit_event_pipeline,
    update_pipeline,
)


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

    return SimpleNamespace(
        create=AsyncMock(side_effect=create),
        update=AsyncMock(side_effect=update),
        read=AsyncMock(),
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


@pytest.mark.asyncio
async def test_create_pipeline_service_stages_without_submission(mock_app):
    backend = _backend()
    services = _services(mock_app, backend)

    with patch("kedro_graphql.pipeline_service.run_pipeline.delay") as delay:
        created = await create_pipeline(
            services,
            _pipeline_input("STAGED"),
            {"email": "user@example.com"},
        )

    assert created.status[-1].state is State.STAGED
    assert all(dataset.tags is not None for dataset in created.data_catalog)
    backend.create.assert_awaited_once()
    backend.update.assert_not_awaited()
    delay.assert_not_called()


@pytest.mark.asyncio
async def test_update_pipeline_service_persists_once_before_submission(
    mock_app,
):
    stored = _staged_pipeline()
    backend = _backend(str(stored.id))
    backend.read.return_value = stored
    services = _services(mock_app, backend)

    with patch("kedro_graphql.pipeline_service.run_pipeline.delay") as delay:
        delay.return_value.task_id = "task-id"
        updated = await update_pipeline(
            services,
            str(stored.id),
            _pipeline_input("READY"),
            {"email": "user@example.com"},
        )

    assert updated.status[-1].state is State.READY
    backend.update.assert_awaited_once()
    assert delay.call_count == 1
    assert delay.call_args.kwargs["parameters"] == {
        "example": "hello",
        "runner_kwargs.is_async": True,
    }


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
    backend.update.assert_awaited_once()
    assert aborted.status[-1].state is State.ABORTING
    assert aborted.status[-1].abort_requested_at is not None


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

    with patch("kedro_graphql.pipeline_service.run_pipeline.delay") as delay:
        delay.return_value.task_id = "task-id"
        created = await submit_event_pipeline(
            services,
            "event00",
            event,
            {"email": "user@example.com"},
        )

    assert [status.state for status in created.status] == [State.READY]
    id_parameter = next(
        parameter for parameter in created.parameters if parameter.name == "id"
    )
    assert id_parameter.value == str(created.id)
    assert id_parameter.type is ParameterType.STRING
    assert all(dataset.tags is not None for dataset in created.data_catalog)
    backend.create.assert_awaited_once()
    backend.update.assert_awaited_once()
    assert delay.call_args.kwargs["parameters"]["id"] == str(created.id)
