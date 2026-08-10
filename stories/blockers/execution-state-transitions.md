# LOCAL-002 owner decisions

- Cause: terminal-state preservation cannot be guaranteed by an in-memory transition table while Mongo updates replace whole documents using only `_id`.
- Affected phase: implementation authorization.
- Evidence: concurrent abort/callback writers can both validate stale STARTED state and last writer wins.
- Recommended decision: authorize a narrow compare-and-set update keyed by pipeline ID, current status slot/state, and status-array size.
- Hard-kill ceiling: define exactly-once cleanup for success, ordinary failure, `SIGINT`, and `SIGTERM`; `SIGKILL` cleanup is necessarily best effort.
- Abort recommendation: conditionally persist ABORTING, issue idempotent Celery abort, allow repeated ABORTING requests to reissue abort, and finalize ABORTED in `after_return`.
- Explicit non-goal: no watchdog/reconciler for a killed parent worker.
- Owner: user.
- Next action: confirm the recommendations and authorize implementation.
- Jira: none; batch is local-only.
