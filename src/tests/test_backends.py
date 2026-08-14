from copy import deepcopy

import pytest

from kedro_graphql.models import State


@pytest.mark.asyncio
async def test_backend_create(mock_app, mock_pipeline_no_task):
    p = await mock_app.state.services.backend.create(mock_pipeline_no_task)
    assert p.id is not None
    p.id = None
    assert p == mock_pipeline_no_task


@pytest.mark.asyncio
async def test_backend_update(mock_app, mock_pipeline_no_task):
    p = await mock_app.state.services.backend.create(mock_pipeline_no_task)
    p.name = "example01"
    p = await mock_app.state.services.backend.update(p)
    assert p.name == "example01"


@pytest.mark.asyncio
async def test_backend_update_status(mock_app, mock_pipeline_no_task):
    p = await mock_app.state.services.backend.create(mock_pipeline_no_task)
    p.status[-1].state = State.STARTED
    p = await mock_app.state.services.backend.update(p)
    assert p.status[-1].state == State.STARTED


@pytest.mark.asyncio
async def test_backend_update_if_current_rejects_stale_status(mock_app, mock_pipeline_no_task):
    backend = mock_app.state.services.backend
    current = await backend.create(mock_pipeline_no_task)
    stale = deepcopy(current)

    current.status[-1].state = State.STARTED
    await backend.update(current)
    stale.status[-1].state = State.ABORTING

    assert await backend.update_if_current(stale, State.STAGED, 1) is None
    assert (await backend.read(id=current.id)).status[-1].state is State.STARTED
