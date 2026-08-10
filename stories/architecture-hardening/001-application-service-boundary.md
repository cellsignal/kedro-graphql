---
story: LOCAL-001
number: 1
slug: application-service-boundary
jira_key: null
local_only: true
model_size: big
model: sol
reasoning: high
depends_on: []
context_from: []
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Application service boundary

## Goal

Move pipeline preparation, creation, update, submission, and abortion out of Strawberry resolvers so GraphQL and REST are adapters over ordinary application functions.

## Rationale

The current mutation resolvers own validation, normalization, persistence, state changes, Celery submission, and audit logging. The CloudEvent route can reuse that behavior only by executing GraphQL documents inside the server, which adds serialization and resolver machinery and makes transport code the de facto domain API.

A shared application boundary is necessary before later stories can safely change execution, subscriptions, or dataset transfer without duplicating business rules. This story is deliberately first because it establishes the callable interface every transport should use.

## Acceptance criteria

- Pipeline operations are callable without constructing Strawberry `Info` or executing a GraphQL document.
- GraphQL mutation names, arguments, response types, permissions, and dry-run behavior remain unchanged.
- The CloudEvent route calls the same application functions as GraphQL and no longer calls `schema.execute()`.
- Event-triggered runs do not stage and then update a pipeline solely to cross an API boundary; persistence occurs only where required by the intended event workflow.
- Application functions receive explicit services and caller identity/audit data rather than reading Strawberry context.
- Generic query extraction used only by the former self-call is deleted, including its static document if no callers remain.
- Enum and list invariants are respected: no raw strings in enum fields and no `None` in list fields.
- Existing mutation, event, dry-run, hook, and application-extension tests pass; direct service tests cover create, update, abort, and event submission.

## Expected files and ownership

- Own: new small function-based pipeline application module.
- Own: mutation bodies in `src/kedro_graphql/schema.py`.
- Own: event route in `src/kedro_graphql/asgi.py`.
- Own: obsolete query-building code in `src/kedro_graphql/utils.py` and `src/kedro_graphql/static/queries.gql` if unused.
- Own: focused schema, event, and service tests.
- Do not redesign query resolvers, signed URLs, worker internals, or public search inputs.

## Risks and checks

- Preserve transaction ordering around persistence and Celery publication.
- Preserve the extension points used by downstream custom FastAPI applications.
- Verify staged, ready, dry-run, retry, and abort paths independently.

## Durable owner decisions

- Use plain functions or one concrete service object; do not introduce an interface hierarchy.
- GraphQL is a transport, not the domain API.
- No compatibility wrapper for GraphQL self-execution.
- Keep `DataSet.config` as JSON text.
