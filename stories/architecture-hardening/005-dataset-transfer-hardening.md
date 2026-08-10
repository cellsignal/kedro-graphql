---
story: LOCAL-005
number: 5
slug: dataset-transfer-hardening
jira_key: null
local_only: true
model_size: big
model: sol
reasoning: high
depends_on: [LOCAL-001]
context_from: [LOCAL-001]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Dataset transfer hardening

## Goal

Resolve dataset transfer targets once, make providers responsible only for signing, and enforce local file security using actual bytes and explicit configuration.

## Rationale

The local and S3 providers independently interpret Kedro dataset configuration, build partition paths, reject unsupported types, and log access. The S3 provider also creates clients inside individual signing calls, so partitioned transfers repeat both business logic and client setup.

The local upload route trusts an optional reported size before copying an unbounded stream, while permissive roots and a placeholder signing secret are valid defaults. Consolidated target resolution reduces divergent behavior; streamed byte enforcement and fail-closed configuration are necessary because these routes cross a filesystem security boundary.

## Acceptance criteria

- One target-resolution path handles ordinary datasets, partitioned datasets, suffixes, and unsupported incremental datasets.
- Local and S3 providers sign resolved targets without duplicating partition/protocol branching.
- S3 uses a reusable injected or lazily cached client rather than creating one client per object.
- Local uploads enforce the configured limit while streaming actual bytes, including when `UploadFile.size` is absent or inaccurate.
- Download and upload token validation share one helper and reject missing filepath claims.
- Path authorization uses resolved paths and explicit roots for both read and write operations.
- Use of the local provider requires an explicitly configured non-placeholder JWT secret.
- Broad `/var` and `/tmp` download defaults are removed.
- Existing GraphQL signed-URL result types and `DataSet.config` JSON representation remain unchanged.
- Tests cover traversal, symlinks, oversize streams, partition paths, client reuse, expired tokens, and unsupported datasets.

## Expected files and ownership

- Own: `src/kedro_graphql/signed_url/*`.
- Own: `/upload` and `/download` routes in `src/kedro_graphql/asgi.py`.
- Own: dataset read/create resolver internals only.
- Own: local-file and S3 provider tests plus configuration tests.
- Do not alter pipeline mutation orchestration or search APIs.

## Risks and checks

- Preserve existing URL and multipart field formats consumed by clients.
- Verify path containment after symlink resolution and before creating directories.

## Durable owner decisions

- Security-sensitive defaults fail closed; do not retain insecure values as alternate modes.
- Keep local and S3 providers as published extension points.
- Do not change `DataSet.config` away from JSON text.
