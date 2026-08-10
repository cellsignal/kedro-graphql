---
story: LOCAL-007
number: 7
slug: plugin-config-cleanup
jira_key: null
local_only: true
model_size: med
model: terra
reasoning: high
depends_on: [LOCAL-004]
context_from: [LOCAL-001, LOCAL-004, LOCAL-005]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Plugin and configuration cleanup

## Goal

Make schema extension discovery application-local, remove example fields from the default production schema, and reduce duplicated configuration surfaces.

## Rationale

Decorator imports currently append types to a process-global registry, so schema contents depend on prior imports and repeated application construction can retain registrations. The default configuration also imports demonstration fields into every production schema.

Configuration is then repeated across Pydantic fields, environment aliases, YAML, and dozens of Click parameters. After `LOCAL-004` removes backend selection, application-local discovery and a smaller operational CLI remove the remaining plumbing without reducing the validated configuration capability.

## Acceptance criteria

- Default application startup imports no example query, mutation, or subscription plugins.
- Building multiple applications in one process cannot leak or duplicate plugin types between schemas.
- Configured imports still support downstream schema extensions with documented deterministic ordering.
- Configuration remains validated through `KedroGraphQLConfig` with the documented precedence.
- CLI retains operational flags such as app/worker/UI/reload/environment/spec path; ordinary application settings use config/env/spec rather than one Click option each.
- Backend selection is absent because MongoDB is the concrete persistence implementation established by `LOCAL-004`.
- Removed CLI options are not retained as aliases or wrappers.
- Application extension examples are updated to the new plugin contract.
- Tests build multiple differently configured apps in one process and prove schema isolation.

## Expected files and ownership

- Own: `src/kedro_graphql/decorators.py`, plugin discovery, and schema construction inputs.
- Own: `src/kedro_graphql/config.py` import defaults.
- Own: `src/kedro_graphql/commands.py` configuration interface.
- May adjust: `src/kedro_graphql/asgi.py` startup wiring after `LOCAL-005`.
- Own: configuration, application, schema-extension tests and relevant docs.
- Do not redesign the app factory or permissions provider.

## Risks and checks

- Published consumers may use decorator-based plugins; preserve the supported extension capability while removing process-global state.
- Verify reload does not accumulate registrations.

## Durable owner decisions

- Example plugins are opt-in examples, never production defaults.
- No process-global mutable plugin registry.
- Prefer one validated configuration interface over mirrored CLI plumbing.
