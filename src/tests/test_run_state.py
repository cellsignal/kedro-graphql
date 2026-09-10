from datetime import datetime, timedelta, timezone

import pytest

from kedro_graphql.models import Pipeline, PipelineStatus, State
from kedro_graphql.run_state import InvalidRunTransition, transition_run


def pipeline(state):
    return Pipeline(name="example", status=[PipelineStatus(state=state)])


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (State.STAGED, State.READY),
        (State.READY, State.STARTED),
        (State.STARTED, State.RETRY),
        (State.RETRY, State.STARTED),
        (State.STARTED, State.ABORTING),
        (State.ABORTING, State.ABORTED),
        (State.STARTED, State.SUCCESS),
        (State.STARTED, State.FAILURE),
    ],
)
def test_transition_run_accepts_lifecycle(source, target):
    run = pipeline(source)

    assert transition_run(run, target)
    assert run.status[-1].state is target


def test_transition_run_owns_timestamps_and_duplicate_delivery():
    run = pipeline(State.READY)
    now = datetime(2026, 8, 14, 8, tzinfo=timezone(timedelta(hours=-4)))

    assert transition_run(run, State.STARTED, now=now)
    assert run.status[-1].started_at == datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    assert not transition_run(run, State.STARTED)
    assert run.status[-1].started_at == datetime(2026, 8, 14, 12, tzinfo=timezone.utc)


def test_transition_run_treats_naive_injected_time_as_utc():
    run = pipeline(State.READY)

    transition_run(run, State.STARTED, now=datetime(2026, 8, 14, 12))

    assert run.current_status.started_at == datetime(
        2026, 8, 14, 12, tzinfo=timezone.utc
    )


def test_transition_run_preserves_terminal_state():
    run = pipeline(State.SUCCESS)

    with pytest.raises(InvalidRunTransition, match="SUCCESS to FAILURE"):
        transition_run(run, State.FAILURE)

    assert run.status[-1].state is State.SUCCESS
