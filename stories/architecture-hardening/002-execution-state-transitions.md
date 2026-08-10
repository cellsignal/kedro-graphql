---
story: LOCAL-002
number: 2
slug: execution-state-transitions
jira_key: null
local_only: true
model_size: big
model: sol
reasoning: xhigh
depends_on: [LOCAL-001]
context_from: [LOCAL-001]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Execution state transitions

## Goal

Make pipeline-run state changes explicit and centralized, then reduce the Celery task and callbacks to a single understandable execution lifecycle.

## Rationale

Run status is currently mutated by GraphQL code, several Celery callbacks, the task body, and subprocess-abort handling. Terminal-state protection and timestamps therefore depend on which callback runs last, and cleanup behavior is repeated across success, failure, and abort paths.

Central transitions are necessary to make retries and duplicate callback delivery safe and to prevent a late callback from overwriting an aborted or failed run. The child process remains valuable; this story simplifies the lifecycle around it rather than removing the isolation it provides.

## Acceptance criteria

- Valid state transitions are implemented once and reject impossible transitions.
- Create, submit, start, retry, abort-requested, aborted, success, and failure timestamps/status fields have one owner each.
- Celery callbacks are idempotent when the pipeline document is missing or a callback is delivered twice.
- Child execution reports one typed outcome: success, failure, or aborted.
- Hook invocation and log flushing occur exactly once for each outcome.
- The worker task no longer duplicates pipeline-slice decoding already provided by `filter_pipeline()`.
- Status persistence failures are logged with pipeline and task IDs and do not silently overwrite terminal states.
- Focused tests cover the transition table, callback idempotence, subprocess outcomes, and abort escalation.

## Expected files and ownership

- Own: `src/kedro_graphql/tasks.py` worker lifecycle and callbacks.
- Own: a small run-state module if needed.
- May adjust: pipeline application service from `LOCAL-001` only for transition calls.
- May adjust: task and abort tests.
- Do not change Mongo connection strategy or remove the backend abstraction; that belongs to `LOCAL-004`.
- Do not change task-ID publication or subscription behavior; that belongs to `LOCAL-003`.

## Risks and checks

- Signals, forked logging handlers, Kedro hooks, and terminal-state preservation are high-risk behavior.
- Test success, ordinary exception, `SIGINT`, `SIGTERM`, retry, and missing-document paths.

## Durable owner decisions

- Keep the child process because it provides real abort isolation.
- Prefer a transition function/table over a state-machine framework.
- Preserve the existing public `State` enum unless a state is proven unused.
