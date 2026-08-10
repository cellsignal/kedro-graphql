---
story: LOCAL-008
number: 8
slug: experimental-surface-pruning
jira_key: null
local_only: true
model_size: small
model: luna
reasoning: medium
depends_on: [LOCAL-007]
context_from: [LOCAL-007]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Experimental surface and dependency pruning

## Goal

Remove unsupported runtime features and make optional features pay for their own dependencies.

## Rationale

Core installation currently includes dependencies for S3, CloudEvents, multipart transfer, every `gql` transport, and a PyPI backport of standard-library `asyncio`. It also ships an Argo runner whose only test is permanently skipped and uses `sh` for operations covered by the standard library.

This increases installation time, resolver conflicts, and maintenance obligations for users who only need the core API. Removing unsupported code and assigning feature dependencies to extras makes the supported surface honest while retaining the optional Panel UI.

## Acceptance criteria

- The unfinished Argo runner and its permanently skipped tests are removed from the runtime package and docs.
- The obsolete PyPI `asyncio` dependency is removed.
- `gql` installs only the transports used by the Python client.
- S3, CloudEvents, local multipart transfer, and UI dependencies are assigned to coherent extras unless required by core startup.
- Installing the core package can import and start the core API without optional feature imports failing.
- UI startup uses `subprocess.run()` and `shutil.move()` instead of `sh`, then removes the `sh` dependency.
- Dead commented UI factories and bundled demonstration code not used by tests/docs are deleted.
- Package metadata and installation documentation list the extras needed for each feature.
- Packaging smoke tests cover core, S3, events, local transfer, and UI import boundaries.

## Expected files and ownership

- Own: `pyproject.toml`, UI startup, Argo package/tests, example runtime code, and installation docs.
- Do not redesign UI components or remove the supported experimental UI itself.
- Do not alter core GraphQL behavior.

## Risks and checks

- Extras must reflect import-time behavior; lazy-import optional modules where necessary.
- Build a wheel and test imports from a clean temporary environment if network/package tooling is available.

## Durable owner decisions

- Unsupported Argo code is removed, not hidden behind a flag.
- The Panel UI remains available as an explicit optional feature.
- Standard-library process and file operations replace `sh`.
