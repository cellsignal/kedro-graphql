---
story: LOCAL-009
number: 9
slug: quality-gates
jira_key: null
local_only: true
model_size: med
model: terra
reasoning: high
depends_on: [LOCAL-002, LOCAL-003, LOCAL-004, LOCAL-005, LOCAL-007, LOCAL-008]
context_from: [LOCAL-001, LOCAL-002, LOCAL-003, LOCAL-004, LOCAL-005, LOCAL-007, LOCAL-008]
authority:
  commit: orchestrator
  push: user
  pr: forbidden
  merge_main: forbidden
  deploy: user
---

# Quality gates

## Goal

Turn the batch's architectural guarantees into reliable local and CI checks without pursuing meaningless blanket coverage.

## Rationale

The repository allows zero coverage, root-level pytest can collect historical source archives, and the unfinished Argo test is permanently skipped. High-risk behavior involving publication failure, process boundaries, signals, uploads, and plugin isolation can therefore regress while the nominal suite remains green.

This story runs last because meaningful gates must measure the architecture that actually survives the batch. Focused failure-path tests and a measured nonzero threshold provide useful protection without forcing tests for incidental UI rendering lines.

## Acceptance criteria

- Default pytest collection targets `src/tests` and does not collect historical archives under `data/tmp`.
- Coverage can no longer pass at zero; set an initial threshold no lower than the measured post-batch core coverage.
- High-risk modules changed by this batch have focused coverage for failure paths, not only successful calls.
- Tests exercise multiprocessing aborts, publication failure, Mongo process boundaries, upload limits, plugin isolation, and optional-import boundaries.
- Strict documentation build and wheel build are part of the documented validation command.
- No permanently skipped production feature test remains.
- The full suite is deterministic when run twice consecutively in the `abd` environment.

## Expected files and ownership

- Own: pytest/coverage configuration, formal tests, and development validation docs.
- Touch production code only to expose deterministic dependency injection proven necessary by a test.
- Do not add a new test framework or a static type checker in this story.

## Risks and checks

- Coverage thresholds must follow measured behavior; do not exclude difficult core code merely to raise the percentage.
- Integration tests requiring Redis or MongoDB must report a clear missing-service blocker.

## Durable owner decisions

- Quality gates measure core operational risk, not UI rendering line count.
- Existing `abd` environment is the canonical local validation environment.
- Static type checking is outside this batch unless separately authorized.
