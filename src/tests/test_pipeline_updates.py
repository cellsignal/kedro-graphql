import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kedro_graphql.exceptions import InvalidPipeline
from kedro_graphql.models import PipelineStatus, State
from kedro_graphql.pipeline_updates import pipeline_updates, reconcile_active_pipelines


def pipeline(state=State.STARTED):
    status = PipelineStatus(state=state, task_id="task")
    return SimpleNamespace(id="pipeline", status=[status], current_status=status,
                           data_catalog=[SimpleNamespace(name="output", config="{}", exists=Mock(return_value=False))])


@pytest.mark.asyncio
async def test_snapshots_change_and_refresh_at_completion():
    current = pipeline()
    services = SimpleNamespace(backend=SimpleNamespace(read=AsyncMock(return_value=current)))
    stream = pipeline_updates(services, "pipeline")
    first = await anext(stream)
    assert first.datasets[0].exists is False
    sleeps = 0
    async def advance(_interval):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            current.data_catalog[0].exists.return_value = True
            current.current_status.state = State.SUCCESS
    with patch("kedro_graphql.pipeline_updates.asyncio.sleep", side_effect=advance):
        final = await anext(stream)
    assert sleeps == 2  # the unchanged intermediate snapshot was not emitted
    assert final.status[-1].state is State.SUCCESS
    assert final.datasets[0].exists is True
    await stream.aclose()


@pytest.mark.asyncio
async def test_existence_failure_is_unknown_and_new_run_refreshes():
    current = pipeline(State.SUCCESS)
    current.data_catalog[0].exists.side_effect = OSError("storage offline")
    services = SimpleNamespace(backend=SimpleNamespace(read=AsyncMock(return_value=current)))
    stream = pipeline_updates(services, "pipeline")
    assert (await anext(stream)).datasets[0].exists is None
    current.data_catalog[0].exists.side_effect = None
    current.data_catalog[0].exists.return_value = True
    current.current_status = PipelineStatus(state=State.READY, task_id="next-task")
    current.status.append(current.current_status)
    with patch("kedro_graphql.pipeline_updates.asyncio.sleep", new=AsyncMock()):
        assert (await anext(stream)).datasets[0].exists is True
    await stream.aclose()


@pytest.mark.asyncio
async def test_missing_pipeline_fails():
    services = SimpleNamespace(backend=SimpleNamespace(read=AsyncMock(return_value=None)))
    with pytest.raises(InvalidPipeline):
        await anext(pipeline_updates(services, "missing"))


@pytest.mark.asyncio
async def test_reconciliation_without_subscribers_isolates_failures_and_cancels():
    first, second = pipeline(), pipeline()
    services = SimpleNamespace(backend=SimpleNamespace(list=AsyncMock(return_value=[first, second])))
    reconcile = AsyncMock(side_effect=[RuntimeError("offline"), None])
    with patch("kedro_graphql.pipeline_updates._reconcile_external", reconcile), patch(
        "kedro_graphql.pipeline_updates.asyncio.sleep", side_effect=asyncio.CancelledError
    ):
        with pytest.raises(asyncio.CancelledError):
            await reconcile_active_pipelines(services)
    assert reconcile.await_count == 2
    assert services.backend.list.call_args.kwargs["limit"] == 0


@pytest.mark.asyncio
async def test_subscription_requires_read_and_subscribe_permissions(mock_app, mock_info_context):
    from kedro_graphql.schema import Subscription
    from kedro_graphql.permissions import AppPermission
    field = next(field for field in Subscription.__strawberry_definition__.fields if field.python_name == "pipeline_updates")
    permissions = field.extensions[0].permissions
    assert [permission.action for permission in permissions] == ["subscribe_to_events", "read_pipeline"]


@pytest.mark.asyncio
async def test_storage_checks_do_not_block_event_loop():
    import threading
    started, release = threading.Event(), threading.Event()
    current = pipeline()
    def slow_exists():
        started.set()
        release.wait(2)
        return True
    current.data_catalog[0].exists.side_effect = slow_exists
    services = SimpleNamespace(backend=SimpleNamespace(read=AsyncMock(return_value=current)))
    snapshots = pipeline_updates(services, "pipeline")
    task = asyncio.create_task(anext(snapshots))
    try:
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.001)
        assert started.is_set()
        assert not task.done()
    finally:
        release.set()
    assert (await task).datasets[0].exists is True
    await snapshots.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("denied_action", ["read_pipeline", "subscribe_to_events"])
async def test_schema_denies_missing_permissions(mock_app, mock_info_context, denied_action):
    def allowed(self, *_args, **_kwargs):
        return self.action != denied_action
    with patch("kedro_graphql.permissions.AppPermission.has_permission", allowed):
        snapshots = await mock_app.state.services.schema.subscribe(
            'subscription { pipelineUpdates(id:"pipeline") { id } }',
            context_value=mock_info_context,
        )
        result = await anext(snapshots)
        assert result.errors
        assert result.data is None
        await snapshots.aclose()


@pytest.mark.asyncio
async def test_api_lifespan_cancels_reconciler_before_backend_shutdown(mock_app):
    started = asyncio.Event()
    cancelled = asyncio.Event()
    async def reconcile(_services):
        started.set()
        try:
            await asyncio.Future()
        finally:
            cancelled.set()
    backend = mock_app.state.services.backend
    async def shutdown():
        assert cancelled.is_set()
    with patch("kedro_graphql.asgi.reconcile_active_pipelines", reconcile), patch.object(
        backend, "startup", new=AsyncMock()
    ), patch.object(backend, "shutdown", new=AsyncMock(side_effect=shutdown)):
        async with mock_app.router.lifespan_context(mock_app):
            await asyncio.wait_for(started.wait(), 1)
        backend.shutdown.assert_awaited_once()
