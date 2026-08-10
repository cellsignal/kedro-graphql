# LOCAL-002 state

- Agent: `/root/local_002_plan`
- Phase: coordination checkpoint
- Parent branch: `codex/architecture-hardening`
- Story branch: `codex/local-002-execution-state-transitions`
- Worktree: `/home/icossentino/code/work/local-002-execution-state-transitions`
- Base commit: `b0350694a6fb8cd7324f4fb2c272fa964383c66c`
- Dependency status: ready; LOCAL-001 accepted and integrated at `b035069`
- Plan: add a small `run_state.py` transition table; centralize field/timestamp ownership; use typed child outcomes; remove duplicate hook/slice/callback logic; add narrow conditional Mongo writes to prevent stale whole-document overwrites
- Changed files: none
- Commits: none
- Checks: complete read-only lifecycle/backend/test inspection; parent combined suite 121 passed with one expected Argo skip; planning worktree and diff checks clean
- Blocker: owner decisions required for Mongo compare-and-set scope and hard-kill cleanup semantics
- Blocker link: `stories/blockers/execution-state-transitions.md`
- Pending Jira sync: none; batch is local-only
- Next action: obtain owner decisions and explicit implementation authorization
- Resume action: resume from branch/worktree at `b035069`; implement `run_state.py` and transition tests first, then conditional persistence and task lifecycle changes

## Planning findings

- `started_at` is currently assigned at READY submission rather than actual STARTED.
- `after_return` can overwrite terminal metadata after success/failure callbacks.
- Child and parent paths duplicate terminal hook handling.
- `abort_triggered` is not used to classify the child outcome.
- `ABORTING` is not in Celery `UNREADY_STATES`, permitting incorrect resubmission checks.
- Whole-document Mongo updates allow stale callback/abort writers to win despite an in-memory transition table.

## Minimum design

- New `run_state.py`: transition table, active/terminal constants, `InvalidRunTransition`, and idempotent `transition_run()`.
- Same-state delivery is a no-op; reruns append a fresh READY status.
- READY owned by submission; STARTED by `before_start`; RETRY by `on_retry`; ABORTING by abort service; SUCCESS/FAILURE by their callbacks; ABORTED by `after_return`.
- Add a narrow conditional Mongo update matching pipeline ID, current status slot/state, and status-array size.
- Replace child string dictionaries with SUCCESS/FAILURE/ABORTED outcomes.
- Cooperative success/failure/SIGINT/SIGTERM cleanup is exactly once; SIGKILL remains best effort.

## Expected changes

- Add: `src/kedro_graphql/run_state.py`, `src/tests/test_run_state.py`.
- Modify: `tasks.py`, `pipeline_service.py`, `pipeline_config.py`, Mongo/base backend, and focused task/service/backend tests.
- Delete: manual slice decoding, repeated callback mutation blocks, unconditional terminal overwrite, duplicate terminal hook calls, and unused lifecycle plumbing.

## Effective authority

- Commit: orchestrator allowed
- Push: user authorization required
- PR: forbidden
- Merge to `main`: forbidden
- Deploy: user authorization required; no deployment is in scope
