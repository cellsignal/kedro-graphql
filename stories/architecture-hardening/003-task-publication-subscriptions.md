---
story: LOCAL-003
number: 3
slug: task-publication-subscriptions
jira_key: null
local_only: true
model_size: small
model: luna
reasoning: high
depends_on: [LOCAL-002]
context_from: [LOCAL-001, LOCAL-002]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Task publication and subscriptions

## Goal

Persist a known Celery task ID before publication and remove subscription polling used only to wait for that ID.

## Rationale

Subscriptions currently query MongoDB every 100 milliseconds until Celery has assigned and persisted a task ID. This creates unnecessary database traffic per subscriber and leaves a race where a subscription can wait indefinitely if publication fails.

Celery already accepts a caller-supplied task ID. Allocating it before publication makes the run record complete before subscribers observe it and turns publication failure into an explicit state transition instead of a polling timeout.

## Acceptance criteria

- Submission generates the task ID before calling Celery and persists it with the ready run status.
- Celery receives the preallocated ID through its native task publication API.
- Pipeline-event and pipeline-log subscriptions never poll MongoDB waiting for `task_id`.
- A subscription to a staged run returns a clear domain error rather than waiting indefinitely.
- Publication failure produces a persisted failure outcome through the transition API from `LOCAL-002`.
- Existing subscription response fields and Python client APIs remain unchanged.
- Tests cover subscription-before-publication, successful publication, publication failure, finished runs, and log streaming.

## Expected files and ownership

- Own: submission calls in the application service.
- Own: subscription resolvers and relevant event monitor code.
- Own: subscription/client tests.
- Touch `tasks.py` only where the preallocated task ID enters the worker.
- Do not replace Celery result-event polling beyond what is required to remove task-ID polling.

## Risks and checks

- Persist-before-publish introduces a publication-failure state that must be explicit.
- Verify concurrent subscribers observe the same task ID and terminal result.

## Durable owner decisions

- Use Celery's native caller-supplied task ID; do not add a second correlation identifier.
- Do not introduce another Redis channel merely to announce the task ID.
