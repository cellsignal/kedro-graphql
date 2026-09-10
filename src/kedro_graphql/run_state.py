from datetime import datetime

from .models import Pipeline, State


TERMINAL_STATES = {State.ABORTED, State.FAILURE, State.SUCCESS}
TRANSITIONS = {
    State.STAGED: {State.READY},
    State.READY: {State.STARTED, State.ABORTING},
    State.STARTED: {
        State.RETRY,
        State.ABORTING,
        State.FAILURE,
        State.SUCCESS,
    },
    State.RETRY: {State.STARTED, State.ABORTING, State.FAILURE},
    State.ABORTING: {State.ABORTED},
}


class InvalidRunTransition(ValueError):
    pass


def transition_run(
    pipeline: Pipeline,
    target: State,
    *,
    now: datetime | None = None,
    **fields,
) -> bool:
    """Apply one valid state change, returning false for duplicate delivery."""
    status = pipeline.current_status
    if status.state is target:
        return False
    if target not in TRANSITIONS.get(status.state, set()):
        raise InvalidRunTransition(f"Cannot transition {status.state.value} to {target.value}")

    now = now or datetime.now()
    status.state = target
    if target is State.STARTED:
        status.started_at = now
    elif target is State.ABORTING:
        status.abort_requested_at = now
    elif target is State.ABORTED:
        status.abort_completed_at = status.finished_at = now
    elif target in {State.FAILURE, State.SUCCESS}:
        status.finished_at = now
    for name, value in fields.items():
        setattr(status, name, value)
    return True
