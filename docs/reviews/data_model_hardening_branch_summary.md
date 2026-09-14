# Data model and execution hardening branch summary

## Executive summary

- [Pipeline updates now preserve a run's identity while refreshing its definition from the selected Kedro pipeline template.](#1-pipeline-updates-preserve-identity-and-refresh-topology)
- [Every persisted pipeline must have a current status, and state changes use guarded updates to avoid acting on a stale run attempt.](#2-current-status-is-an-explicit-model-invariant)
- [GraphQL inputs and stored models now round-trip without losing supported fields, while unexpected entity fields are rejected instead of silently ignored.](#3-model-conversion-is-lossless-for-supported-data-and-strict-about-unknown-data)
- [Pipeline timestamps are normalized to UTC so API and database values have consistent meaning across environments.](#4-pipeline-timestamps-have-consistent-utc-semantics)
- [Pipeline-template IDs and pagination are now stable, human-readable, and independent of discovery order.](#5-pipeline-template-identity-and-pagination-are-stable)
- [Runners can persist namespaced metadata on a run, giving external systems a durable correlation mechanism.](#6-runner-extension-metadata-is-durable-and-namespaced)
- [MongoDB used by local development and CI was upgraded from 4.2 to 4.4 to match the current PyMongo client.](#7-development-and-ci-use-a-pymongo-compatible-mongodb-version)
- [Pipeline catalogs and parameter defaults are now resolved from server-managed, per-pipeline Kedro configuration at submission time.](#8-pipeline-configuration-is-resolved-and-owned-by-the-server)
- [Celery task identity is reserved and stored before publication, and broker publication failures become visible pipeline failures.](#9-task-publication-has-a-durable-identity)
- [External runners can reconcile and terminate work through a generic lifecycle owned by the API.](#10-the-api-owns-a-generic-external-runner-lifecycle)
- [Final dataset paths are generated before a pipeline is stored or published, so every consumer sees one final configuration.](#11-final-dataset-paths-are-persisted-atomically)
- [Submitted configuration is checked for embedded credentials and bounded by a configurable payload-size limit.](#12-configuration-is-checked-for-secrets-and-transport-size)
- [The package's built-in Argo implementation was removed; applications now provide external-runner integrations through the generic lifecycle.](#13-the-bundled-argo-runner-was-removed)
- [Worker execution now uses the stored pipeline as its source of truth and gives one child process ownership of the Kedro runner, catalog, hooks, and session context.](#14-worker-execution-has-one-source-of-truth-and-one-process-owner)
- [The main hardening train was published as `kedro-graphql==1.5.2.dev4`; the later worker-lifecycle refactor remains an additional branch change.](#15-development-package-and-release-notes-were-updated)

## Scope

This document describes the changes on `codex/data-model-hardening` since its
merge base with `main` (`70fb853`). It is based on both the commit history and
the resulting source, test, API specification, and documentation changes. At the
time of writing, the branch contains 19 non-merge commits and changes 51 files,
with 2,346 additions and 913 deletions.

The sections below describe coherent changes rather than treating every commit
as a separate feature. Supporting test-only commits and follow-up documentation
commits are grouped with the behavior they support.

## 1. Pipeline updates preserve identity and refresh topology

**Problem.** An update request could supply a different pipeline name and could
leave the stored description or node topology out of step with the selected
Kedro pipeline template. The abort path also read the same record more than
once, creating unnecessary opportunities for two reads to observe different
states.

**Architecture change.** Update processing now loads the stored pipeline first,
uses that record as the identity authority, and rejects attempts to rename it.
When an update selects a template, the service refreshes the template-owned
description and node graph as well as the catalog and parameters. Abort handling
reuses its initial read instead of fetching the record again.

**Before.** A client could accidentally make the name in an update disagree with
the persisted identity, and a pipeline could retain stale nodes or descriptive
information after its execution configuration changed.

**After.** A pipeline ID and name continue to identify the same run throughout
its life. Updating a run refreshes the parts derived from the current template,
so the API's displayed topology matches what will execute. Developers extending
the update flow should treat identity as immutable and template topology as
server-owned.

**Related commit:** `d6503b6` (`fix(pipelines): preserve update identity and topology`).

## 2. Current status is an explicit model invariant

**Problem.** Callers repeatedly accessed the last item in a pipeline's status
history directly. A malformed stored pipeline with no statuses therefore failed
with a generic list error, and each caller had to reproduce the same assumption.
Concurrent operations also needed a consistent way to reason about which run
attempt they were changing.

**Architecture change.** `Pipeline.current_status` is now the single model-level
access point for the active status. It raises a domain-specific error when the
history is empty. Reads and lists validate this invariant, and service, schema,
task, and UI code use the property rather than indexing the list. State writes
continue through compare-and-set operations that identify the expected task and
state.

**Before.** Invalid data could travel farther through the application and fail
in inconsistent places. Code added around pipeline state commonly repeated
`status[-1]`, making it easy to omit validation or operate on a superseded
attempt.

**After.** Missing status history is rejected clearly at the model or storage
boundary. Extension code can use `current_status` and gets the same invariant as
the built-in API. Concurrent state changes are less likely to update or publish
work for the wrong attempt.

**Related commit:** `a7b7b56` (`fix(pipelines): enforce current status invariant`).

## 3. Model conversion is lossless for supported data and strict about unknown data

**Problem.** Converting a stored pipeline back into an editable input omitted
dataset tags, parent relationships, and hooks. Conversely, generic dictionary
conversion silently ignored unknown fields, which could make a misspelled or
outdated field appear to have been accepted even though it was discarded.

**Architecture change.** Pipeline-to-input conversion now carries all supported
editable fields through the round trip. Entity `from_dict` conversion rejects
unknown keys, including in nested entities. A separate, deliberate
`Pipeline.from_input` boundary distinguishes persistent entity data from
command-only GraphQL controls such as requested state, runner selection,
slicing, and `onlyMissing`. MongoDB removes its internal `_id` before invoking
the strict model conversion.

**Before.** Read-modify-write clients could unintentionally erase supported
metadata. Typos and stale payload fields could be silently lost, making client
and server behavior hard to diagnose.

**After.** Supported model data survives a round trip, while unsupported entity
fields fail early with a useful error. API developers can still add
operation-specific controls, but must explicitly decide whether a field belongs
to the persistent model or only to an API command. This makes schema evolution
more visible and prevents accidental persistence behavior.

**Related commits:** `1157f18` (`fix(models): preserve pipeline input round trips`)
and `b5f031e` (`fix(models): reject unknown entity fields`).

## 4. Pipeline timestamps have consistent UTC semantics

**Problem.** Naive and timezone-aware datetime values could enter the model with
different interpretations. That made comparisons, serialization, and display
dependent on the process timezone or on where a value originated.

**Architecture change.** Pipeline creation and state-transition timestamps are
generated in UTC. Incoming aware timestamps are converted to UTC, while naive
timestamps are interpreted as UTC rather than local time. Test fixtures now use
the same convention.

**Before.** Two visually similar timestamps could refer to different instants,
and behavior could vary between a developer machine and a deployed worker.

**After.** Stored and returned timestamps describe one unambiguous instant.
Clients may convert UTC values for display, and extension code should supply
timezone-aware values when it knows the source timezone.

**Related commits:** `250f2ca` (`fix(models): normalize pipeline timestamps to utc`)
and `6e13d34` (`test(models): use utc pipeline fixtures`).

## 5. Pipeline-template identity and pagination are stable

**Problem.** Template IDs were generated values tied to discovery order. A
restart or ordering change could therefore change IDs and invalidate cursors or
bookmarks even when the available pipelines had not changed.

**Architecture change.** A pipeline template now uses its pipeline name as its
ID. Templates are sorted consistently, and cursor handling supports string IDs,
including names containing colons or Unicode characters.

**Before.** The same pipeline could appear under a different opaque ID after an
application change, and pagination depended on incidental registration order.

**After.** Template IDs are predictable and remain stable as long as pipeline
names remain stable. API clients can retain cursors and references more safely,
and developers adding a pipeline can reason about its externally visible ID
without reproducing an object-ID generator.

**Related commit:** `f559655` (`fix(models): stabilize pipeline template ids`).

## 6. Runner extension metadata is durable and namespaced

**Problem.** A runner that starts work in another system needs to retain values
such as an external job or workflow ID. There was no general place to persist
that correlation data, so an integration risked keeping important state only in
worker memory or adding runner-specific fields to the core pipeline model.

**Architecture change.** Pipeline statuses can now contain string metadata whose
keys begin with `x-`. The metadata is persisted, exposed through GraphQL and the
client, and supplied to runners through their run context. Runners receive an
`emit_metadata` callback so they can record correlation values while work is
starting. Multiple metadata events may be persisted before the runner returns.

**Before.** Restarting a worker could lose the information needed to find an
external execution, or each integration had to modify the shared schema.

**After.** External integrations can record their own namespaced values without
changing the framework model. Later reconciliation and termination can recover
those values from the stored run. Extension authors should choose stable `x-`
keys and string representations for any data required after the initial task
process exits.

**Related commit:** `49962ff` (`feat(runners): persist extension metadata`).

## 7. Development and CI use a PyMongo-compatible MongoDB version

**Problem.** The local and CI services used MongoDB 4.2, which no longer matched
the capabilities expected by the current PyMongo client. This made otherwise
valid tests fail because of infrastructure version skew.

**Architecture change.** The MongoDB container image in Docker Compose and the
GitHub Actions service was raised from 4.2.24 to 4.4.29.

**Before.** Developers and CI could encounter driver/server compatibility errors
that were unrelated to the API behavior being tested.

**After.** Local Compose and CI exercise the code against the same supported
MongoDB baseline. No API contract changes, but developers must be able to run
MongoDB 4.4 rather than relying on the former 4.2 image.

**Related commit:** `f6da089` (`fix(ci): align mongodb service with pymongo`).

## 8. Pipeline configuration is resolved and owned by the server

**Problem.** Callers were expected to construct and submit a complete resolved
catalog and parameter set. That duplicated Kedro configuration behavior in API
consumers, made centrally managed defaults difficult, and coupled a configuration
change to client logic or an application image rebuild.

**Architecture change.** Runtime configuration now includes a required
`pipeline_config_sources` allowlist mapping exposed API pipeline names to
runtime-mounted Kedro configuration directories. Project metadata contains the
project path, exposed Kedro pipelines, and per-pipeline configuration sources.
At submission, the service loads the selected source, resolves optional
request-time Kedro globals, merges explicit client catalog and parameter
overrides, and normalizes the result for the selected pipeline slice. Dotted
parameter overrides update nested values using Kedro-compatible semantics.

The selected slice matters: if slicing removes the node that normally creates a
dataset, that dataset becomes a free input for this invocation and a client may
provide its catalog entry. Unknown pipelines, missing or empty sources,
unresolved globals, and incomplete resolved catalogs fail before persistence.

**Before.** An API consumer needed enough knowledge of the hosted Kedro project
to reproduce its catalog and default parameters. Adding or changing an exposed
configuration commonly required coordinated client or image changes.

**After.** A normal caller can select a pipeline and submit only intentional
overrides or required free inputs. The hosting application controls which
pipelines are exposed and which configuration each uses. When Python code and
dependencies are already installed, operators can mount updated configuration
and restart the service without rebuilding the package image. Developers can
still support specialized runs through explicit catalog and parameter
overrides; those inputs augment or replace resolved entries rather than forming
a second submission mode.

**Configuration impact.** Deployments must define at least one
`pipeline_config_sources` entry. The mapping can be supplied through YAML or the
`KEDRO_GRAPHQL_PIPELINE_CONFIG_SOURCES` environment variable. Relative paths are
resolved against the Kedro project root.

**Related commit:** `f2888dd` (`feat(pipelines): resolve runtime-owned configuration`).

## 9. Task publication has a durable identity

**Problem.** A run was stored as `READY` before Celery allocated its task ID.
During that gap, the database could not identify the work that was about to be
published. A broker error could also leave a run looking ready even though no
worker could ever receive it.

**Architecture change.** The service now creates a task UUID before publication,
stores it with the `READY` status, and calls Celery with that exact ID.
Publication uses a common helper that records a `FAILURE` transition when the
broker call fails. Create, update, and event-triggered execution all follow this
ordering.

**Before.** API responses and subscriptions could temporarily lack a task ID,
publication errors could strand a run, and concurrent operations had a weaker
correlation between the stored attempt and the queued task.

**After.** The persisted run identifies the intended Celery task before any
message leaves the API process. Clients can observe that identity immediately,
and a dispatch failure becomes an explicit terminal state. Extension code that
publishes work should preserve this store-before-publish ordering rather than
calling `delay()` directly.

**Related commit:** `c504a7b` (`fix(tasks): persist identity before publication`).

## 10. The API owns a generic external-runner lifecycle

**Problem.** Starting an external job is only part of managing it. Reads need to
discover completed work, aborts need to request cancellation, and deletes must
not remove the correlation data while work is still active. The framework did
not have runner-neutral operations for those responsibilities.

**Architecture change.** External runner classes can implement
`ExternalRunnerLifecycle`, which defines `reconcile()` and `terminate()`.
The service reconstructs a runner from the stored import path and arguments,
supplies the persisted run context and `x-` metadata, and invokes lifecycle
operations during reads, aborts, and deletes. Reconciliation returns a confirmed
state or no change. Termination requests do not themselves claim the work has
stopped.

**Before.** External execution state could drift from the API record. An abort
might be reported as finished before the remote system confirmed it, or a delete
could discard the only durable handle for active work.

**After.** Reading a pipeline can reconcile its recorded state with the external
system. An external abort remains `ABORTING` until reconciliation confirms a
terminal outcome, and deletion is refused while termination remains unconfirmed.
Developers adding a remote backend implement the two generic operations and use
status metadata for correlation; the core API does not need backend-specific
fields.

**Related commit:** `886f3d3` (`feat(runners): own external execution lifecycle`).

## 11. Final dataset paths are persisted atomically

**Problem.** Pipeline creation previously inserted one version of the run and
then updated it after generating unique dataset paths. The API response, stored
record, and worker message could briefly or permanently disagree, especially if
a worker started quickly or the second write failed.

**Architecture change.** The service reserves the MongoDB object ID before the
insert, generates unique paths against that identity, and performs one create
with the final pipeline. The Mongo backend honors a preassigned model ID. Update
also completes path generation before its guarded persistence operation.

**Before.** Observers or workers could see provisional paths, and pipeline
creation depended on a second mutation succeeding.

**After.** The stored pipeline, returned API object, and published execution all
use the same final paths. Dataset names are safe to consume as soon as creation
returns. Developers extending creation should finish all identity-dependent
normalization before the single persistence boundary.

**Related commit:** `7e27013` (`fix(pipelines): persist final paths atomically`).

## 12. Configuration is checked for secrets and transport size

**Problem.** A resolved catalog or parameter set could embed passwords, tokens,
private keys, or cloud access keys and then be stored in MongoDB or carried in a
task message. Very large configurations could also exceed practical MongoDB,
Celery, or downstream workflow transport limits.

**Architecture change.** The submission boundary recursively rejects known
credential-bearing field names and inline `credentials` mappings. A named
credential reference such as `credentials: production-s3` remains valid. The
resolved catalog and parameters must be JSON serializable and their compact
UTF-8 representation must not exceed `pipeline_submission_max_bytes`, which
defaults to 1 MiB and must be positive.

**Before.** Sensitive values could be copied into durable API records, and a
payload might fail only after persistence or during transport.

**After.** Credential material must come from Kedro credential providers,
workload identity, or another external secret mechanism. Oversized or
non-serializable configuration is rejected before storage and publication.
API extenders should pass credential references, not resolved secrets, and can
raise the size limit through configuration only when the complete transport
path supports it.

**Related commit:** `753c3e8` (`feat(pipelines): enforce configuration boundaries`).

## 13. The bundled Argo runner was removed

**Problem.** The package contained an unused Argo Workflows runner, template,
tests, documentation, and development-cluster wiring. It embedded one external
system's assumptions in the framework while the new generic lifecycle provided
the appropriate extension boundary.

**Architecture change.** The in-tree `ArgoWorkflowsRunner` and its template,
exports, and tests were deleted. Development cluster setup no longer installs or
exposes Argo. The framework retains only the generic runner initialization,
metadata, reconciliation, and termination contracts.

**Before.** An application could import the package's Argo class, but the API
owned an implementation it did not actively use and that was not the production
integration for the consuming application.

**After.** Applications that use Argo provide their own runner and implement the
generic external lifecycle. Imports of the removed class must be replaced; no
parallel compatibility path remains. Developers gain a smaller framework
surface and can evolve backend-specific behavior in the application that owns
it.

**Related commit:** `dbf4092` (`refactor(runners): remove in-tree argo implementation`).

## 14. Worker execution has one source of truth and one process owner

**Problem.** `run_pipeline` mixed configuration discovery, task orchestration,
Kedro session setup, catalog construction, hooks, process supervision, and state
persistence. It inferred the project root from the installed
`kedro_graphql` package, duplicated persisted pipeline fields in the Celery
message, kept mutable catalog state on a process-scoped task object, and built
different catalogs in the parent and child processes. Hooks could therefore
observe a catalog different from the one the runner actually used.

**Architecture change.** The worker now retains the explicit Kedro project path
received at startup. Session creation lives in the project runtime layer and
selects the configuration source for the stored pipeline. The Celery task takes
the required pipeline ID plus request-only slice controls; it reloads the
pipeline name, catalog, parameters, runner, hooks, and metadata from the stored
record.

Catalog construction is centralized. The child process constructs and owns the
runner, execution catalog, hook manager, selected pipeline, and execution hook
lifecycle. A parent catalog is used only when planning `only_missing`. The code
no longer mutates or reads private Kedro session attributes, and persistence of
filtered nodes uses the same missing-record and compare-and-set handling as
other task writes. Child tracebacks are returned to the parent and included in
the raised execution error.

**Before.** Installing the package outside its source repository could point a
session at the wrong project. A queued message, backend record, and mutable task
attribute could disagree. Hook-driven catalog changes were not guaranteed to
affect execution, and retries could use serialized values that no longer matched
the durable run definition.

**After.** The persisted pipeline is the execution contract, and the worker
locates the project and per-pipeline configuration explicitly. All execution
hooks see the exact catalog given to the runner. Retries and callbacks recover
runner configuration from durable state, while the parent process concentrates
on planning, supervising, and recording the outcome. Developers extending task
execution should add durable fields to the pipeline model or explicit
request-only controls rather than duplicating configuration in Celery kwargs.

Abort races are also handled more predictably: a task that observes an existing
`ABORTING` state or loses its startup state transition exits as aborted, and a
local runner result of `aborted` is persisted as `ABORTED` rather than ordinary
success.

**Related commit:** `9a448d4` (`refactor(tasks): harden pipeline execution lifecycle`).

## 15. Development package and release notes were updated

**Problem.** The consuming application needed a concrete package containing the
main hardening train, and the release record needed to describe the actual
configuration and CLI surface.

**Architecture change.** The package version was raised from `1.5.2.dev3` to
`1.5.2.dev4`. The changelog records server-owned configuration, durable task
publication, external lifecycle behavior, atomic paths, submission boundaries,
and removal of the bundled Argo runner. A follow-up restored the documented CLI
flags for Celery abort polling and grace-period settings, and the execution plan
records the development package as published.

**Before.** Downstream projects had no recorded package version containing that
train, and the release notes briefly did not match the existing CLI.

**After.** Downstream dependency declarations can target
`kedro-graphql==1.5.2.dev4`, and the repository records that build as the
published integration artifact. This is a development release rather than a
new stable-version declaration. The `9a448d4` worker-lifecycle refactor was
committed after that publication, so the current branch tip contains one
additional change that is not established here as part of the published
`1.5.2.dev4` artifact.

**Related commits:** `7cdc287` (`build(package): release 1.5.2.dev4`),
`f4c3388` (`docs(package): record published release`), and `d8a3d84`
(`docs(package): align release notes with cli`).

## Combined behavior for API consumers

A typical submission is now smaller and more deterministic. The caller chooses
an exposed pipeline, optionally selects a slice, and supplies only deliberate
catalog or parameter overrides and any free inputs created by that slice. The
server resolves the canonical Kedro configuration, validates that no embedded
secrets or excessive payload is present, generates final dataset paths, stores
the complete run with a reserved task ID, and then publishes that exact run.

Once execution starts, the worker reloads the durable definition instead of
trusting a duplicate task payload. Local work is owned by one child process and
its hooks see the runner's real catalog. External work can publish correlation
metadata and remains manageable after the launching task exits. Reads reconcile
external state, and abort or delete operations retain the record until remote
termination is confirmed.

The main externally visible tightening is intentional: malformed model fields,
unknown or unconfigured pipelines, incomplete configuration, embedded secrets,
oversized payloads, and pipeline renames now fail at clear boundaries instead
of being silently ignored or failing later.

## Migration guide for existing applications

This section is for maintainers upgrading an application that already embeds or
deploys Kedro-GraphQL. The required work depends on whether the application uses
only the standard CLI and local Kedro runners or also supplies custom startup,
models, clients, or external runners.

### 1. Choose the correct package source and upgrade MongoDB

The main hardening train through removal of the bundled Argo runner was recorded
as this published build:

```text
kedro-graphql==1.5.2.dev4
```

The final worker-lifecycle refactor (`9a448d4`) was added afterward. To adopt
every behavior described in this document, use the current branch tip or a later
package release that contains that commit. Do not assume the recorded
`1.5.2.dev4` artifact contains the final refactor. Once this branch is released,
pin the resulting immutable version rather than a moving branch reference.

Upgrade local, CI, and deployed MongoDB services from 4.2 to a version compatible
with the installed PyMongo client. This branch tests against MongoDB 4.4.29. Do
not update only Docker Compose: the test service and deployed environment should
use the same supported baseline.

Before rolling out the API, take the normal database backup appropriate for the
deployment and check existing pipeline documents for an empty `status` array.
Every pipeline must now contain at least one status entry. Repair or remove
invalid records before they are read through the new model; the application now
rejects them instead of failing later with a list-index error.

Existing timestamps do not require a schema rewrite solely for this release.
The model interprets naive values as UTC and normalizes aware values when they
are loaded. If the application historically wrote naive local time rather than
naive UTC, correct that data explicitly before relying on the new interpretation.

### 2. Define the pipelines exposed by the API

Add `pipeline_config_sources` to Kedro-GraphQL configuration. The application
will not start with an empty mapping. Each key must exactly match a pipeline
registered in the Kedro project, and each value must point to a Kedro
configuration root containing the usual `base` and environment directories.

For example:

```yaml
config:
  env: production
  pipeline_config_sources:
    daily_analysis: conf/api/daily-analysis
    sample_qc: /runtime/kedro-config/sample-qc
  pipeline_submission_max_bytes: 1048576
```

The same mapping can be supplied as an environment variable when configuration
is injected at deployment time:

```bash
export KEDRO_GRAPHQL_PIPELINE_CONFIG_SOURCES='{"daily_analysis":"conf/api/daily-analysis","sample_qc":"/runtime/kedro-config/sample-qc"}'
```

Relative paths resolve from the Kedro project root; absolute paths are used as
provided. Mount every referenced directory into both the API and worker
containers at the same path. Ensure the selected `env` exists in each source
and that catalogs, parameters, globals, dataset factories, and named credential
references resolve without access to developer-local files.

`conf_source` may still configure other Kedro-GraphQL behavior, but it is no
longer the source of truth for a submitted pipeline's catalog and parameters.
Do not keep a caller-side copy of the complete resolved catalog as an alternative
configuration path. The per-pipeline source replaces that responsibility.

### 3. Simplify and validate pipeline submissions

Update API clients so a normal pipeline submission contains the pipeline name
and only the values specific to that invocation:

- parameter overrides;
- intentional dataset overrides;
- free-input datasets required by the selected slice;
- optional request-time Kedro globals;
- execution controls such as state, slices, hooks, and `onlyMissing`.

Clients may continue sending a complete catalog during a transition if every
entry is a deliberate override, but they no longer need to resolve server
defaults themselves. Removing that duplicated resolution is preferable because
the server configuration should be authoritative.

Request-time `globals` must be a JSON object. Dotted parameter names such as
`options.retries` update the corresponding nested server default. Validate any
generated input against the current GraphQL schema: entity conversion now
rejects unknown fields rather than silently dropping them. If a client was
depending on ignored fields, either remove them or deliberately add them to the
appropriate persistent model or operation input.

Do not submit inline credentials or fields named like passwords, tokens, API
keys, private keys, or cloud access keys. Replace them with named Kedro
credential references:

```yaml
orders:
  type: pandas.CSVDataset
  filepath: s3://company-data/orders.csv
  credentials: production-s3
```

Provide the referenced secret through the application's Kedro credential
provider or use workload identity. Verify the fully resolved catalog and
parameters fit within `pipeline_submission_max_bytes`; raise the limit only
after confirming MongoDB, Celery, and any external workflow transport can carry
the larger value safely.

### 4. Update custom application and worker bootstrap code

Applications using the standard `kedro gql` command already pass the project
path correctly. Custom launchers must make the same information explicit:

- call `load_project_metadata(project_path, config)` after bootstrapping the
  Kedro project;
- pass that metadata to the application factory;
- call `celery_app(config, backend, project_path)` when constructing a worker.

`ProjectMetadata` now contains `project_path`, the exposed `pipelines`, their
`config_sources`, and generated `templates`. It no longer provides one global
`catalog` and `parameters` mapping. Replace custom code that reads those removed
fields with `load_pipeline_configuration(metadata, config, pipeline_name,
globals)`.

The API and worker must start with the same Kedro project code, environment, and
`pipeline_config_sources` mapping. A worker must not infer the project root from
the installed `kedro_graphql` package directory.

If application code publishes the internal Celery task directly, stop passing a
duplicate name, catalog, parameters, runner, or hooks. The supported task
message contains the stored pipeline ID and request-only execution controls:

```python
run_pipeline.apply_async(
    kwargs={"id": pipeline_id, "slices": slices, "only_missing": only_missing},
    task_id=reserved_task_id,
)
```

Normal application integrations should call the pipeline service rather than
publishing this task themselves. The service reserves and stores the task ID,
records publication failures, and prevents the message from getting ahead of
the database record.

### 5. Update code that extends pipeline models or state handling

Replace direct access to `pipeline.status[-1]` with
`pipeline.current_status`. Treat a pipeline's name and ID as immutable after
creation. Update handlers may change invocation details, but attempting to
rename an existing pipeline now fails.

Review every custom `from_dict` caller and persisted extension field. Model
entities now reject unknown keys. Operation-only inputs such as slices, desired
state, and `onlyMissing` belong on `PipelineInput`; persistent fields belong on
the entity model. Do not add an unvalidated catch-all mapping simply to preserve
previously ignored data.

Template IDs are now pipeline names. Clear or migrate client caches, bookmarks,
and stored pagination cursors that contain the former generated IDs. New cursors
remain stable as long as registered pipeline names remain stable.

Status timestamps returned by the API should be treated as UTC. Convert them at
the presentation edge rather than applying a server-local timezone assumption.

### 6. Migrate custom and external runners

A local runner that completes inside the worker can continue using the normal
Kedro runner interface. Runner constructor arguments continue to come from the
resolved `runner_kwargs` parameter mapping.

A runner whose work outlives the Celery task must also inherit
`ExternalRunnerLifecycle` and implement:

```python
from kedro_graphql.models import State
from kedro_graphql.runners import ExternalRunnerLifecycle


class RemoteRunner(ExternalRunnerLifecycle, ExistingKedroRunner):
    def terminate(self) -> None:
        external_id = self.run_context["metadata"]["x-external-id"]
        request_remote_cancellation(external_id)

    def reconcile(self) -> State | None:
        external_id = self.run_context["metadata"]["x-external-id"]
        return confirmed_remote_state(external_id)
```

During `run()`, record every value needed to find the remote execution later:

```python
self.emit_metadata({"x-external-id": str(external_id)})
```

Metadata keys must start with `x-`, and values must be strings. The runner's
`run_context` contains `pipeline_id`, `task_id`, and the current metadata
mapping. `terminate()` should request cancellation but should not report success
prematurely. `reconcile()` returns a `State` only after the remote system
confirms it, or `None` when the stored state should remain unchanged.

Replace imports of `kedro_graphql.runners.argo.ArgoWorkflowsRunner` with an
application-owned runner. Move its Argo template, client setup, workflow
submission, termination, and reconciliation into the application repository.
There is no package-level Argo path to retain alongside the new implementation.

Be aware that reading an externally managed pipeline can now reconcile and
persist a confirmed state. Review custom authorization, audit, and caching code
that assumed reads never write. Abort and delete flows must retain the pipeline
and its metadata until the remote execution is confirmed terminal.

### 7. Check hooks and task execution assumptions

Execution hooks now run in the child process and receive the same catalog that
the runner uses. Remove workarounds that copied parent-process catalog mutations
into the runner. Hook code must be safe to initialize and run in the child and
must not depend on mutable state left on the Celery task object.

The stored pipeline is now the source of truth for name, resolved catalog,
parameters, runner, hooks, and runner metadata. If an extension needs a value on
retry or after worker restart, persist it on the appropriate model rather than
attaching it to the task instance or relying on a duplicated message argument.

For `onlyMissing`, remember that the parent may build a planning catalog, while
the child creates the execution catalog. Only child-process execution hooks
should modify runtime behavior.

### 8. Roll out and verify in dependency order

Use this sequence to avoid starting new code without its required configuration:

1. Upgrade and back up MongoDB, then audit stored pipelines for missing status
   histories and incorrectly interpreted naive timestamps.
2. Mount and validate every per-pipeline Kedro configuration source in the API
   and worker environments.
3. Deploy the application configuration containing `pipeline_config_sources`
   and an intentional submission-size limit.
4. Deploy application code updated for strict models, the new metadata shape,
   and any custom bootstrap or runner changes together with the current branch
   build or a later release containing `9a448d4`. Use `1.5.2.dev4` only when the
   final worker-lifecycle refactor is intentionally out of scope.
5. Restart both API and worker processes so they load the same project metadata
   and configuration mapping.
6. Query pipeline templates and confirm their IDs match the configured pipeline
   names.
7. Stage one pipeline without publishing it and inspect the resolved catalog,
   parameters, UTC timestamp, and generated dataset paths.
8. Run one local pipeline and confirm hooks, task identity, result state, and
   dataset paths.
9. If applicable, run one external pipeline, confirm its `x-` metadata survives
   a worker restart, then test reconciliation, abort, and guarded deletion.
10. Submit one invalid unknown field, embedded credential, unresolved global,
    and oversized payload to confirm each is rejected before persistence or
    task publication.

The migration is complete when clients no longer synthesize server defaults,
the API and workers resolve the same per-pipeline configuration, durable records
contain valid status history and task correlation, and external runners can be
managed entirely from persisted metadata.

## Commit-to-change map

| Commit | Change represented in this summary |
| --- | --- |
| `d6503b6` | Update identity and template topology |
| `a7b7b56` | Current-status invariant and guarded state use |
| `1157f18`, `b5f031e` | Lossless, strict model conversion |
| `250f2ca`, `6e13d34` | UTC timestamp semantics and fixtures |
| `f559655` | Stable template IDs and cursors |
| `49962ff` | Durable runner extension metadata |
| `f6da089` | MongoDB/PyMongo service compatibility |
| `f2888dd` | Server-owned runtime pipeline configuration |
| `c504a7b` | Durable task identity before publication |
| `886f3d3` | Generic external-runner lifecycle |
| `7e27013` | Atomic final dataset paths |
| `753c3e8` | Credential and payload-size boundaries |
| `dbf4092` | Removal of the bundled Argo runner |
| `7cdc287`, `f4c3388`, `d8a3d84` | Development release and release-note bookkeeping |
| `9a448d4` | Worker and `run_pipeline` lifecycle refactor |

Merge commits in the history integrate these feature commits into the branch;
they do not introduce additional user-visible behavior and are therefore not
listed as separate changes.
