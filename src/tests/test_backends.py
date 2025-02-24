from kedro_graphql.models import State


def test_backend_create(mock_app, mock_pipeline_no_task):
    p = mock_app.backend.create(mock_pipeline_no_task)
    assert p.id is not None
    p.id = None
    assert p == mock_pipeline_no_task


def test_backend_update(mock_app, mock_pipeline_no_task):
    p = mock_app.backend.create(mock_pipeline_no_task)
    p.name = "example01"
    p = mock_app.backend.update(p)
    assert p.name == "example01"


def test_backend_update_status(mock_app, mock_pipeline_no_task):
    p = mock_app.backend.create(mock_pipeline_no_task)
    p.status[-1].state = State.STARTED
    p = mock_app.backend.update(p)
    assert p.status[-1].state == State.STARTED
