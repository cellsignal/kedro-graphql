# LOCAL-005 state

- Agent: `/root/local_005_plan`
- Phase: coordination checkpoint
- Parent branch: `codex/architecture-hardening`
- Story branch: `codex/local-005-dataset-transfer-hardening`
- Worktree: `/home/icossentino/code/work/local-005-dataset-transfer-hardening`
- Base commit: `b0350694a6fb8cd7324f4fb2c272fa964383c66c`
- Dependency status: ready; LOCAL-001 accepted and integrated at `b035069`
- Plan: central target resolver over persisted dataset config; providers sign resolved targets only; shared local JWT/path validation; bounded atomic uploads; app-scoped S3 client lifecycle
- Changed files: none
- Commits: none
- Checks: complete read-only source/test/doc inspection; parent combined suite 121 passed with one expected Argo skip; planning worktree and diff checks clean
- Blocker: owner decisions required for secret strength, symlink race ceiling, operation-bound JWT claims, and transfer policy details
- Blocker link: `stories/blockers/dataset-transfer-hardening.md`
- Pending Jira sync: none; batch is local-only
- Next action: obtain owner decisions and explicit implementation authorization
- Resume action: resume branch/worktree at `b035069`; implement target resolver and focused tests before provider and route changes

## Minimum design

- Parse persisted `DataSet.config` once and resolve ordinary/partitioned targets, protocols, suffixes, and invalid incremental datasets.
- Providers receive resolved targets and only sign them; remove S3-to-local delegation.
- Instantiate providers per app; inject or lazily reuse S3 clients and close only provider-owned clients.
- Register local routes only for `LocalFileProvider`.
- Decode JWTs through one helper, resolve roots/targets before containment checks, and enforce streamed byte limits.
- Upload through a sibling temporary file, clean it on failure, and atomically replace the destination on success.
- Preserve GraphQL result shapes, local URL/multipart fields, and `DataSet.config` JSON text.

## Expected changes

- Modify: signed URL base/local/S3 providers, local routes in `asgi.py`, dataset resolver internals, config, focused tests, configuration/provider docs, and generated API docs.
- Likely add: `src/tests/test_signed_url/test_base.py`.
- Preserve: pipeline service/mutations, models, permissions, commands, client, and dependencies.

## Effective authority

- Commit: orchestrator allowed
- Push: user authorization required
- PR: forbidden
- Merge to `main`: forbidden
- Deploy: user authorization required; no deployment is in scope
