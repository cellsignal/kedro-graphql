---
story: LOCAL-004
number: 4
slug: mongo-storage-boundary
jira_key: null
local_only: true
model_size: big
model: sol
reasoning: xhigh
depends_on: [LOCAL-003, LOCAL-005]
context_from: [LOCAL-001, LOCAL-002, LOCAL-003, LOCAL-005]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Mongo storage boundary

## Goal

Remove the unused backend abstraction and the background asyncio loop/thread bridge while giving the ASGI process and synchronous Celery workers native MongoDB access.

## Rationale

MongoDB is the only persistence implementation. The base backend, dynamic import path, initializer, and backend-selection configuration add indirection without supporting a real alternative. At the same time, the asynchronous Mongo implementation is a good fit for FastAPI but a poor fit for synchronous Celery lifecycle callbacks. The worker compensates with a process-scoped background thread and event loop while Mongo clients are separately tracked by event loop and process ID.

Removing the abstraction lets the application construct concrete Mongo persistence directly. Sharing document conversion while giving each runtime native database access removes the thread/loop machinery and makes process ownership explicit.

## Acceptance criteria

- `BaseBackend`, dynamic backend discovery, and `init_backend()` are deleted.
- `KedroGraphQLConfig.backend` and the corresponding CLI option are deleted.
- Application startup constructs the concrete Mongo persistence implementation directly.
- ASGI resolvers continue to use non-blocking PyMongo operations.
- Celery callbacks and tasks use synchronous, post-fork-safe persistence without `run_sync()`.
- API and worker persistence share pipeline document encoding/decoding and query semantics.
- Worker clients are created after fork and closed through Celery process lifecycle signals.
- `run_sync()` and its global loop/thread registry are deleted when no callers remain.
- Mongo configuration remains validated and supplies both runtimes.
- Documentation describes MongoDB as the persistence implementation, not one selectable backend.
- Removed backend extension paths are not retained as aliases, wrappers, or configuration options.
- Tests cover API async persistence, worker sync persistence, fork/client recreation, and equivalent CRUD results.

## Expected files and ownership

- Own: deletion of `src/kedro_graphql/backends/base.py` and dynamic backend initialization.
- Own: concrete Mongo construction in application and worker startup.
- Own: Celery app/worker process hooks.
- Own: removal of `run_sync()` from task callbacks.
- Own: Mongo and task persistence tests plus backend-extension documentation removal.
- Do not redesign pipeline transitions or subscription semantics completed by preceding stories.

## Risks and checks

- This crosses process, thread, and event-loop boundaries; require focused fork tests.
- Ensure synchronous database calls never move into ASGI request handlers.

## Durable owner decisions

- Share document mapping, not connection objects or async interfaces, between API and workers.
- Do not keep the async worker path behind a configuration flag.
- No new database abstraction framework.
- MongoDB is the only supported persistence implementation; adding another store later requires a new architectural decision based on a real use case.
- Do not preserve the backend import path or base class for external compatibility.
