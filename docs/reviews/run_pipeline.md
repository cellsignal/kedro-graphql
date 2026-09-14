# `run_pipeline` review

Scope: `src/kedro_graphql/tasks.py:468-743`, including the startup,
configuration, persistence, hook, and child-process code that supplies it.

Status: resolved in priority order. The implementation now uses the persisted
pipeline as the execution source of truth, creates sessions from explicit
project configuration, and constructs the runner, hooks, pipeline, and catalog
inside the execution child. The regression suite covers session configuration,
minimal task publication, process-local execution dependencies, catalog identity
across hooks, missing records, and child traceback propagation.

## Findings

### 1. High: the task derives the project root from the installed package

`run_pipeline` creates its session with
`Path(__file__).resolve().parent.parent.parent` (`tasks.py:478`). That happens to
point at this repository during a source checkout, but it does not identify the
Kedro project when `kedro_graphql` is installed in `site-packages` or when the
command is launched for another project.

The correct project path already exists at the worker boundary:
`start_worker(config, project_path)` receives it and calls
`bootstrap_project(project_path)` (`commands.py:29-32`). `celery_app()` then
stores the backend and configuration but drops `project_path`
(`celeryapp.py:7-27`). Preserve that value in the worker's runtime dependencies
and use it when creating a session. Do not infer runtime configuration from the
library's source location.

The session also uses the process-wide `config.conf_source`, while the current
application resolves a distinct source per pipeline through
`ProjectMetadata.config_sources` and `load_pipeline_configuration()`
(`project.py:13-32`). Because the submitted catalog and parameters are already
resolved before publication, the session's configuration source is disconnected
from the configuration that will actually execute.

### 2. High: a mutable Celery task attribute is a second catalog source of truth

`before_start()` conditionally sets `self.kedro_graphql_pipeline`, and
`run_pipeline` conditionally reads it to merge a catalog (`tasks.py:503-510`). A
Celery task object is process-scoped, so the attribute can survive into a later
invocation. It is never cleared when logging is disabled, setup fails, or the
next task starts. A later run can therefore merge catalog entries from another
pipeline.

The pipeline is already re-read from the backend at `tasks.py:490`. Use that
record's serialized catalog as the sole source, including the log datasets added
by `before_start()`, and remove the task attribute and the catalog task argument
once callers no longer need it. This also removes the current three-way
duplication among task kwargs, backend state, and task-local state.

### 3. High: hooks observe a different catalog from the runner

The parent creates and populates `io` (`tasks.py:512-523`) and calls
`after_catalog_created` and `before_pipeline_run` on it. The child independently
creates and populates another catalog (`tasks.py:412-420`) and passes that one to
the runner. Any hook mutation performed during either parent callback is absent
from the catalog that executes. The terminal callbacks then receive the child
catalog, so one hook lifecycle spans two different objects and two processes.

Create the execution catalog and run all execution hook callbacks in the child.
If the parent needs a catalog for `only_missing` planning, name and limit it as a
planning catalog; do not present it to execution hooks. This makes the child the
single owner of runner, catalog, and hook lifecycle.

### 4. Medium: session ownership is ceremonial and depends on Kedro internals

The task mutates `session._hook_manager` and reads `session._project_path`
(`tasks.py:488,533`), both private attributes. The hook-manager assignment has
no effect on execution because the code calls `runner_instance.run()` directly
rather than `session.run()`. `session.load_context()` is invoked only to recover
the environment for `record_data`, causing context/configuration loading that is
otherwise unused.

Put session construction and run metadata in one project-runtime helper outside
`tasks.py`. That helper should accept the explicit project path and typed config,
return only public values needed by the task, and contain any unavoidable Kedro
private access in one place. Remove the unused `_hook_manager` assignment. If no
session store or Kedro session hook is required, the smaller consistent design is
to remove the session and generate an execution ID directly; do not retain a
session that does not own execution.

### 5. Medium: catalog and parameter assembly is duplicated

Parent and child both call `DataCatalog.from_config()`, construct the same
parameter feed dictionary, loop through `add_param_to_feed_dict()`, and add it to
the catalog (`tasks.py:512-523` and `412-420`). This duplication caused finding
3 and gives the two paths room to diverge further.

Move the existing eight-line assembly sequence into one function in
`pipeline_config.py` and call it wherever a catalog is genuinely required. The
parent should avoid constructing one at all except for `only_missing` planning
and pre-fork validation.

### 6. Medium: `run_pipeline` repeats data already available from the persisted run

The task accepts `name`, `parameters`, `data_catalog`, `runner`, and `hooks`, then
also loads the pipeline record. Those values are persisted on that record before
publication (`pipeline_service.py:422-443`), but execution trusts the duplicated
message values. This permits the message and backend record to disagree and
makes every future field change touch both publication and execution code.

Publish only the run ID plus request-only execution controls that are not stored.
After the task loads the record, derive the pipeline name, resolved catalog,
resolved parameters, runner, hooks, and metadata from it. This also makes retries
execute the recorded run definition instead of an independently serialized copy.

### 7. Medium: state updates do not consistently use the task's guarded helpers

The method correctly routes writes through `_update_current()`, but after
`before_pipeline_run` it reads the pipeline again and immediately dereferences it
without checking for a missing record (`tasks.py:590-592`). Similar missing/stale
handling is already centralized in `_transition()` and `_persist_runner_metadata()`.

Add one task method for updating filtered node names with the same missing-record
and compare-and-set behavior. This is the root location for that invariant and
keeps backend race handling out of the orchestration body.

### 8. Low: control-flow bookkeeping obscures who owns error callbacks

`child_owns_terminal_hook` is created only after `child.start()` and the exception
handler probes `locals()` to determine whether to call `on_pipeline_error`
(`tasks.py:626,734-742`). This is fragile implicit state. The child traceback is
also discarded at `tasks.py:729`, and `raise e` at `tasks.py:743` needlessly
re-raises through a new frame.

Moving all execution hooks into the child removes the ownership flag entirely.
Return the child's traceback as part of a small result value for logging, and use
a bare `raise` for parent-side failures.

### 9. Low: the public signature claims inputs are optional when the body requires them

`parameters` and `data_catalog` default to `None`, but the method immediately
calls `.items()` on `parameters` and passes `data_catalog` to catalog creation.
`name` and `runner` are also required for a valid execution. The publisher always
sends them, so the defaults describe an unsupported call shape.

After reducing the message to the run ID, make that ID required. Until then,
remove `None` defaults from required arguments so direct/eager calls fail at the
boundary with a useful signature error.

## Recommended order

1. Pass the explicit project path into worker runtime state and centralize session
   creation.
2. Make the persisted pipeline record the only execution configuration source;
   remove `kedro_graphql_pipeline` task state.
3. Move catalog construction and the complete execution-hook lifecycle into the
   child, retaining a parent planning catalog only for `only_missing`.
4. Shrink `run_pipeline` to orchestration: load run, prepare execution, supervise
   child, persist outcome.

No feature flags or parallel execution paths are warranted. These changes should
replace the duplicated paths rather than preserve both designs.
