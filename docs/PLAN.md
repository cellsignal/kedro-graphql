# Kedro-GraphQL execution hardening plan

## Scope

This plan contains only work owned by `/home/icossentino/code/kedro-graphql`.
AB Discovery integration and its production Argo runner are tracked separately
in the AB Discovery repository's `docs/PLAN.md`. No task or commit may span the
two repositories.

## Required baseline

The existing `codex/data-model-hardening` branch is the merge-train parent, not
merely a source branch for a new train. It is substantially ahead of `main` and
already contains:

- pipeline update identity and topology preservation;
- a current-status invariant and compare-and-set transition hardening;
- lossless input/model conversion and unknown-field rejection;
- UTC timestamp normalization and stable pipeline-template IDs;
- `x-`-prefixed runner extension metadata and runner context;
- the MongoDB CI compatibility fix.

Treat those commits as incorporated prerequisites. Do not recreate them as new
tasks. Before starting the first task branch, verify the merge-train tip and
preserve its commits throughout the train.

## Simplified goal execution

Run this plan as one goal without Jira issues or story files. Reuse
`/home/icossentino/code/work/kedro-graphql-data-model` and its existing
`codex/data-model-hardening` branch as the merge-train parent; do not create
another integration branch. For each task, create an individual feature branch
from the current merge-train tip, implement and verify it in the worktree, then
merge the accepted task branch back into `codex/data-model-hardening` before
starting any dependent task. Work sequentially in the one worktree.

Push only the merge-train branch and open one final Kedro-GraphQL pull request to
`main`. Task branches remain local unless explicitly requested otherwise. After
this train lands, publish the version consumed by the separate AB Discovery
merge train.

## Existing metadata implementation

Commit `49962ff` (`feat(runners): persist extension metadata`) already provides
the framework portion of runner status metadata:

- metadata keys must use the `x-` prefix and values must be strings;
- status metadata is persisted and exposed through GraphQL;
- runners receive `emit_metadata` and run context from the task process.

Do not recreate this work. Preserve it in the merge train and verify it remains
covered. AB Discovery is responsible for making its runner emit the Argo values.

## Tasks

### 1. Resolve server-managed pipeline configuration on submission

Make canonical catalog templates and defaults server-owned rather than requiring
callers to synthesize the complete catalog. Do not remove the ability for a
client to submit explicit catalog entries: free inputs and deliberate dataset
overrides remain valid request data. Determine free inputs from the selected
pipeline slice, not only from the complete pipeline. If a slice omits an
upstream producer, its output becomes a free input for that invocation and the
client must be able to submit its catalog entry.

The pipeline-name mapping and referenced Kedro configuration are runtime inputs
provided by the hosting application. They must not be baked into the
Kedro-GraphQL package or service image. A configuration deployment and process
rollout must be sufficient to add or change an API pipeline when its Python code
is already installed; only code or dependency changes require a new image.

- Add an explicit runtime-supplied pipeline-name-to-config-source mapping.
- Accept request-time Kedro globals for the selected source.
- Load and resolve the source's catalog and parameters, merge submitted catalog
  entries and parameters as explicit overrides, then normalize, validate,
  persist, and publish the resulting pipeline. Validate catalog completeness
  against the selected slice.
- Keep nested parameter handling inside Kedro-GraphQL; callers must not need a
  copy of Kedro's parameter-flattening behavior.
- Reject unknown pipelines, missing sources, unresolved globals, and invalid
  resolved catalogs at the submission boundary.
- Add focused tests for multiple runtime config sources, globals, dataset factories,
  slice-created free inputs, and invalid configuration.

This task replaces caller-side construction of the complete resolved catalog; it
does not remove the existing client catalog-input capability. Do not add a
second optional submission mode for the superseded path.

### 2. Finish durable publication identity

The baseline already protects current-status transitions with compare-and-set
updates, but create still persists `READY` before `delay()` allocates the task
ID. Allocate the Celery task ID before publication, persist it atomically with
the `READY` transition, and publish using that exact ID. Record publication
failure explicitly. Preserve the existing transition checks so concurrent
updates cannot publish duplicate executions or update the wrong run attempt.

Acceptance requires focused concurrency and publication-failure tests.

### 3. Define runner lifecycle operations

The baseline already implements explicit `ABORTING` and `ABORTED` transitions
for the local Celery/child-process lifecycle. Extend that model so generic
create, read, update, abort, and delete behavior can own an external runner
execution without embedding Argo-specific fields in the framework model.

- Use persisted `x-` extension metadata as the runner correlation boundary.
- Let a runner inspect, terminate, and reconcile its external execution.
- Keep abort status at `ABORTING` until the runner confirms a terminal outcome.
- Retain durable status and correlation data until termination is confirmed.
- Add framework tests with a small fake external runner; do not import AB
  Discovery or implement Argo behavior here.

### 4. Make final paths atomic

The baseline update path applies `generate_unique_paths()` before persistence,
but create still persists and then mutates the pipeline. Apply final path
generation before both create persistence and task serialization. Use one final
immutable payload for the stored pipeline, API response, and worker invocation.
Cover create and update with one focused regression test each.

### 5. Bound and validate submitted configuration

Reject known credential-bearing fields before persistence and enforce a
submission-size limit suitable for Mongo, Celery, and downstream workflow
transport. Keep credentials in external secret providers or workload identity.

Add boundary tests for accepted references, rejected credential fields, and an
oversized submission.

### 6. Remove the deprecated in-tree Argo runner

Delete Kedro-GraphQL's `ArgoWorkflowsRunner`, its templates, exports, tests, and
documentation. It is deprecated and unused. The only supported Argo runner is
`ab_discovery.runners.argo.ArgoRunner`, which remains in the AB Discovery
repository; do not move or duplicate that implementation here.

### 7. Release for AB Discovery

Run the full Kedro-GraphQL test and packaging checks, update release notes and
versioning as required by the repository, publish the resulting package, and
record the exact version for the AB Discovery plan. The release must contain the
`codex/data-model-hardening` baseline as well as this merge train. Publishing is
the dependency gate between the two repository merge trains.

Release candidate: `kedro-graphql==1.5.2.dev4`.

## Merge order

1. Server-managed runtime configuration resolution.
2. Durable publication identity.
3. Generic runner lifecycle operations.
4. Atomic final paths.
5. Configuration bounds and credential rejection.
6. Deprecated Argo runner removal.
7. Combined checks and release.

Each task gets its own feature branch and local acceptance checkpoint before it
is merged into the Kedro-GraphQL merge train. Open only the final merge-train PR.
