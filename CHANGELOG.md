# Changelog

## [Unreleased]

Added:

- Test for catalog recreation in child process to prevent fork-safety issues with S3 and MongoDB connections
- `DataSetInput.list_partitions` flag to support partition discovery in `readDatasets`
- `readDatasets` schema coverage for partition discovery and partition-specific signed URL flows
- Schema tests to cover baseline read datasets, list partitions, and partition-specific signed URL behavior
- Documentation updates for partitioned datasets with a clear two-step flow (discover partitions, then request signed URLs)
- `ABORTED` to both `PipelineInputStatus` and pipeline `State` enums so clients can request and observe pipeline aborts through GraphQL
- `ABORTING` pipeline state and `abort_requested_at` / `abort_completed_at` timestamps on `PipelineStatus` for explicit abort lifecycle tracking
- `KEDRO_GRAPHQL_CELERY_ABORT_POLLING_INTERVAL` (default `5`) for controlling abort check frequency in Celery task execution (values below `1` second are clamped at runtime)
- `KEDRO_GRAPHQL_CELERY_ABORT_GRACE_PERIOD` (default `60`) for controlling how long the worker waits before escalating abort signals (values below `5` seconds are clamped at runtime)
- CLI flags `--celery-abort-polling-interval` and `--celery-abort-grace-period` on `kedro gql` to override the above settings
- Schema mutation tests for aborting a running pipeline and rejecting abort requests for non-running pipelines
- Documentation updates for log subscriptions, including custom log capture guidance and refreshed `pipelineLogs` examples

Changed:

- `PipelineEvent.timestamp` is now always a UTC ISO 8601 string (e.g. `"2026-05-14T12:55:52.779094"`). Live subscription events previously emitted a Unix epoch float from `time.time()` where as already-completed pipeline events previously passed the raw `datetime` object for `finished_at` so there was an inconsistency
- `read_datasets` now supports returning `DataSet` for partition discovery requests
- `KedroGraphqlTask` now inherits from Celery `AbortableTask`
- `run_pipeline` now executes the Kedro runner in a child subprocess while the parent task monitors abort status and sends OS signals (`SIGINT` first, then escalation)
- `updatePipeline` now handles `state: ABORTED` by calling `AbortableAsyncResult.abort()` and persisting `ABORTING` in the document backend until worker-side abort completion; repeated abort requests while already `ABORTING` or `ABORTED` return without error
- Task `on_success` and `on_failure` handlers now preserve abort states and avoid overwriting `ABORTING`/`ABORTED` with `SUCCESS` or `FAILURE`
- Pipeline subscription events now map Celery `SUCCESS` with result `aborted` to `ABORTED` so streamed status aligns with pipeline abort semantics
- Task-scoped log stream handlers are now attached to the root logger so propagated logs from Kedro and custom modules are captured consistently
- Task subprocess logging reinitializes stream handlers in the child process to keep Redis stream publishing process-local after fork

Fixed:

- Catalog now recreated in child process to prevent fork-safety errors with S3 (`TextDataset` with S3 protocol) and MongoDB connections; connections are now created fresh in the child process instead of inherited from parent
- Mismatch in types `ObjectId` and `str` caused the `readTemplates` query to always fail
- Celery task callback null-safety in `before_start`, `on_success`, and `on_retry` when pipeline records are missing
- `after_return` temp log cleanup logging bug (`.name` used on string path)
- Kedro log handlers added during pipeline runs are now removed from the `kedro` logger (not the task module logger), tagged per Celery task id, reducing duplicate log output and teardown noise
- Pipeline `State` enum typo corrected from `RECIEVED` to `RECEIVED`
- `PipelineLogStream` now always closes async Redis connections with `aclose()` via `finally`, including subscription cancellation/disconnect paths
- `PipelineLogStream` terminal state detection now includes explicit `ABORTED` status
- Plugin registration logs now use correct labels for mutation and subscription plugin types
- `MongoBackend` now detects fork boundaries and recreates `MongoClient` per process to eliminate fork-safety warnings
- Celery config now sets `broker_connection_retry_on_startup=True` to suppress deprecation warning for future Celery 6.0 compatibility
- Child pipeline process now handles `SIGINT`/`SIGTERM` gracefully during abort so logs flush and hook-based log persistence still run before exit
- Tests now use an isolated Redis DB and flush it before/after the session to clean up Celery result keys and stream artifacts

## [1.5.1] - 2026-03-31

Added:

- **`.dockerignore` File**: Added a `.dockerignore` to exclude unnecessary files (docs, tests, logs, notebooks, data, IDE configs, etc.) from the Docker build context for faster builds and smaller images
- **Docker Compose Profiles**: The `kedro-graphql` service now uses a `profiles` key (`app`), so it is only started when explicitly requested via `docker compose --profile app up`
- **Development Docs**: Added a Docker section to `docs/development.md` covering image builds, `.dockerignore` usage, and Docker Compose profile usage

## [1.5.0] - 2026-03-31

Added:

- **Configurable Lifespan Handler**: `KedroGraphQL` now accepts an optional `lifespan_handler` parameter, allowing child classes to provide custom lifespan handlers for startup/shutdown logic
- **Runner Kwargs via Parameters File**: The Kedro parameters file now supports a `runner_kwargs` key, allowing runner constructor arguments (e.g., `is_async: true`) to be configured at runtime
- **Comprehensive Concurrency Tests**: New test suite for WebSocket subscription concurrency, including parallel pipeline event/log subscriptions and event loop responsiveness assertions

Changed:

- **All GraphQL Resolvers Now Async**: Every query, mutation, and subscription resolver is now `async def`, with all blocking backend/database calls wrapped in `run_in_threadpool` to prevent event loop blocking
- **Async Pipeline Event Monitor**: Celery `AsyncResult` property access in `PipelineEventMonitor.start()` is now wrapped in `run_in_threadpool` with error handling for missing/disabled result backends
- **Async Pipeline Log Stream**: Task status checking in `PipelineLogStream` is now wrapped in `run_in_threadpool`, and the Redis connection uses `aclose()` for proper async cleanup
- **Runner Initialization**: `init_runner()` now accepts `**runner_kwargs` and instantiates the runner directly, rather than returning the class for inline instantiation

Fixed:

- **Blocking WebSocket Connections**: Synchronous Celery and database operations in async resolvers no longer block the event loop, fixing stalled WebSocket subscriptions with multiple concurrent clients (fixes #88)
- **Null Safety in Task Callbacks**: `on_failure()` and `after_return()` now check if the pipeline record exists before accessing `status`, preventing `AttributeError`
- **Redis Connection Cleanup**: Changed `close()` to `aclose()` for proper async Redis connection cleanup in log streaming
- **CloudEvents Dependency**: Pinned `cloudevents` to `>=1.12.0,<2.0.0` to avoid breaking API changes in 2.0.0 that removed `cloudevents.http`, `cloudevents.pydantic`, and `cloudevents.conversion` submodules
- **FastAPI WebSocket Route**: Updated `add_websocket_route` to `add_api_websocket_route` for compatibility with FastAPI >=0.135.0 where the old method was removed

## [1.4.0] - 2025-10-26

Added:

- **Enhanced Signed URL Support**: New `SignedUrl`, `SignedUrls`, and `SignedUrlField` models for structured signed URL responses
- **Partitioned Dataset Example**: Added `timestamped_partitions` node and `timestamped_partitioned` dataset to example01 pipeline for demonstrating partitioned dataset functionality
- **Enhanced UI for Partitioned Datasets**: 
  - Modal viewer for exploring individual partitions within PartitionedDatasets
  - Bulk download functionality for selected partitions
  - Improved data catalog explorer with better partition handling
- **Utility Methods**: Added `get_field_value()` method to `SignedUrl` for easy field extraction

Changed:

- **Breaking Change - GraphQL Schema**: `read_datasets` and `create_datasets` now return `List[SignedUrl | SignedUrls | None]` instead of raw strings/dicts
- **Breaking Change - Client API**: Both `read_datasets()` and `create_datasets()` methods now return structured `SignedUrl`/`SignedUrls` objects instead of raw responses
- **Enhanced Signed URL Providers**: Both `LocalFileProvider` and `S3Provider` now return structured `SignedUrl`/`SignedUrls` objects
- **UI Improvements**:
  - Data Catalog Explorer renamed from "Explorer" to "Catalog" tab
  - Better error handling and user notifications for unsupported dataset operations
  - Enhanced dataset configuration parsing using `parse_config()` method
- **Updated Test Suite**: Comprehensive test updates to work with new structured signed URL responses

Fixed:

- **GraphQL Union Types**: Proper implementation of union types for signed URL responses with `__typename` support
- **S3Provider Logging**: Corrected log messages to show `create_dataset` instead of `read_dataset` for upload operations
- **Dataset Configuration Handling**: Better support for both `filepath` and `path` dataset configurations
- **Partition File Handling**: Improved file naming and path construction for partitioned datasets

## [1.3.1] - 2025-10-23

Fixed:

- support generating unique file paths for partitioned datasets when the create_pipeline and update_pipeline mutations are called

## [1.3.0] - 2025-10-23

Added:

- Support for partitioned datasets in signed URL providers
- `DataSetInput` model with optional `partitions` field for specifying which partitions to work with
- New exception classes `DataSetConfigError` and `DataSetError` for better error handling
- Enhanced dataset parsing utility methods: `parse_config()`, `parse_filepath()`, and `parse_path()` in DataSet model
- Comprehensive test coverage for partitioned datasets including read/create operations for specific partitions
- Mock S3 testing with proper fixtures for partitioned dataset operations

Changed:

- **Breaking change**: `create_datasets` method signature changed from `names: list[str]` to `datasets: list[DataSetInput]` for enhanced flexibility with partitioned datasets
- Migrated from deprecated FastAPI event handlers (`@app.on_event`) to modern lifespan pattern using `@asynccontextmanager`
- Enhanced LocalFileProvider and S3Provider with refactored URL signing logic and better partition support
- Restructured test files with dedicated package for signed URL tests
- Updated GraphQL schema mutations to support new dataset input format
- Improved logging for partition operations

Fixed:

- Application lifecycle management using proper async context management for backend startup/shutdown
- Code formatting and whitespace issues
- Enhanced error handling for dataset configuration parsing


## [1.2.0]

Added:

- command-line flags for all configuration options, including complex data types support using JSON strings
- proper configuration loading order (YAML spec > CLI flags > Environment variables > .env file > Defaults)
- support for comma-separated strings, JSON arrays, and single values for list-type configuration options
- `test_config.py` with unit tests for configuration precedence and data type parsing scenarios
- `root_path` configuration option to support API endpoint prefixing
- support for both `X-Forwarded-*` and `x-auth-request-*` header formats for OAuth2 proxy compatibility
- client URI configuration options for GraphQL client (`client_uri_graphql` and `client_uri_ws`) with defaults and full CLI/environment variable support

Changed:

- `configuration.md` with alphabetical ordering and detailed examples for different data types
- alphabetically sorted all spec-*.yaml files
- some panel UI components for better async handling and loading states using `pn.state.onload`

Removed:

- some outdated documentation

Fixed:

- proper error handling in load_api_spec() to prevent crashes on YAML parsing errors
- race conditions in Panel components by ensuring proper loading order
- S3 provider key handling for files without directory prefixes
- panel server kwargs configuration in UI specs
- made `unique_paths` parameter optional with default `None` in `create_pipeline` and `update_pipeline` mutations to fix issue where passing empty string `""` was converted to `['']` (a truthy list) causing unexpected calls to `generate_unique_paths`
- configuration loading where CLI defaults for `conf_source` and `env` were being passed directly to `start_app` and `start_worker` instead of using the values from the merged configuration that includes the YAML spec file.

## [1.1.1] - 2025-08-01

- fix schema plugin discovery

## [1.1.0] - 2025-07-30

Added

- create_datasets mutation, read_datasets query, both use signed URL to facilitate uploads/downloads

- `kedro_graphql.permissions` module and classes

- authentication configuration examples

- support API and UI yaml specifications

- mkdocs site

- an experimental UI, see the [UI](./docs/ui.md) docs.

- a python client with CRUD and subscription support to facilitate integration with other python applications

  ```
  import json
  from kedro_graphql.models import Pipeline, PipelineInput, TagInput
  from kedro_graphl.client import KedroGraphqlClient
  
  client = KedroGraphqlClient(uri="http://0.0.0.0:5000/graphql",
                              ws="ws://0.0.0.0:5000/graphql")
  
  input_dict = {"type": "text.TextDataset", "filepath": "s3://example/text_in.txt"}
  output_dict = {"type": "text.TextDataset", "filepath": "s3://example/text_out.txt"}

  pipeline_input = PipelineInput(**{
      "name": "example00",
      "state": "STAGED",
      "data_catalog": [{"name": "text_in", "config": json.dumps(input_dict)},
                       {"name": "text_out", "config": json.dumps(output_dict)}],
      "parameters": [{"name": "example", "value": "hello"},
                     {"name": "duration", "value": "0", "type": "FLOAT"}],
      "tags": [{"key": "author", "value": "opensean"},
               {"key": "package", "value": "kedro-graphql"}]
  })

  ## create a pipeline
  pipeline = await client.create_pipeline(pipeline_input)

  ## subscribe to pipeline events
  async for event in client.pipeline_events(id=pipeline.id):
      print(event.timestamp, event.status)

  ## subscribe to pipeline logs
  async for log in client.pipeline_logs(id=pipeline.id):
      print(log.time, log.message)

  ## read a pipeline
  pipeline = await client.read_pipeline(id=pipeline.id)

  ## read pipelines
  pipelines = await client.read_pipelines(limit=5, filter="{\"tags.key\": \"package\", \"tags.value\": \"kedro-graphql\"}")

  ## update a pipeline
  pipeline_input.tags.append(TagInput(key="test-update", value="updated"))
  pipeline = await client.update_pipeline(id=pipeline.id, pipeline_input=pipeline_input)

  ## delete a pipeline
  pipeline = await client.delete_pipeline(id=pipeline.id)

  ## close all sessions
  await client.close_sessions()
  ```

- [gql](https://gql.readthedocs.io/en/stable/) dependency in requirements.txt for the client
- a `def delete_pipeline_collection` pytest fixture that will drop the "pipelines" collection after all tests have finished
- encode and decode functions for the Pipelines, Pipeline, PipelineEvent, PipelineLogs, and PipelineInput objects
- support for native `strawberry.Schema` keyword arguments in `kedro_graphql.schema.build_schema` wrapper

Changed

- using python's tempfile in pytest fixtures for efficient cleanup after testing
- Removed the private `kedro_pipelines_index` field from the Pipeline object to decouple from application
  - the `nodes` and `describe` fields of the Pipeline object are now set when the `create_pipeline` mutation is called rather than resovled upon query

Fixed

- `on_pipline_error` to `on_pipeline_error` typo in `hooks.py`

Security

- Upgraded `strawberry-graphql` from `~=0.233.0` to `~=0.262.5` to address [CVE-2024-47874](https://github.com/advisories/GHSA-f96h-pmfr-66vw)
- Upgraded `fastapi` from `~=0.111.0` to `~=0.115.11` to address [CVE-2024-47082](https://github.com/advisories/GHSA-79gp-q4wv-33fr) and [CVE-2025-22151](https://github.com/advisories/GHSA-5xh2-23cc-5jc6)

## [1.0.1] - 2025-02-26

Added

- Auto register `DataValidationHooks` and `DataLoggingHooks` in pyproject.toml using multiple entrypoints

Changed

- Changed README.md img src to absolute URLs for PyPi's project description renderer
- Moved `after_catalog_created` kedro hook call after `record_data` is loaded into memory in `tasks.py` because it's needed in the `on_pipeline_error` kedro hook call
- KedroGraphQL configurable application import to `from kedro_graphql.asgi import KedroGraphQL`

Removed

- Default rich handler from `logging.yml` so that saved log files and streamed subscription logs do not show colorized console markup

Fixed

- Critical bug caused by an unused import in `__init__.py` that prevented KedroGraphQL app from starting
- `on_pipline_error` kedro hook typo. changed to `on_pipeline_error`

## [1.0.0] - 2025-02-21

Added

- `sort` argument to pipelines Query so users could sort through mongodb document fields lexicographically (ascending/descending)
- Support for presigned S3 urls for upload and download of `DataSet`
- `tags` and `exists` fields to `DataSet` type
- `parent`, `runner`, `created_at` fields to `Pipeline` type
- `updatePipeline` and `deletePipeline` mutations
- Universal logs handling with `gql_meta` and `gql_logs` DataSets, `KEDRO_GRAPHQL_LOG_TMP_DIR` and `KEDRO_GRAPHQL_LOG_PATH_PREFIX` env variables, and `DataLoggingHooks`
- Support for `Pipeline` slicing with `PipelineSlice` and `PipelineSliceType` types and `slices` and `only_missing` fields
- Nested parameters using dot-list notation in the `Parameter.name`
- Kedro hook calls in `run_pipeline` task:
  - `after_catalog_created`
  - `before_pipeline_run`
  - `after_pipeline_run`
  - `on_pipeline_error`
- `project_version`, `pipeline_version`, and `kedro_graphql_version` fields to `Pipeline` type

Changed

- `Pipeline` status field refactored with `PipelineStatus`
- Renamed schema fields to follow CRUD naming conventions (`createPipeline`, `readPipelines`, `readPipeline`)
- Back-end interface refactored to improve `Pipeline` object updates and prevent race conditions

Removed

- The following fields of the `Pipeline` and `PipelineInput` types:
  - `filepath`
  - `load_args`
  - `save_args`
  - `type`
  - `credentials`
- The following fields of the `Pipeline` and `PipelineInput` types:
  - `inputs`
  - `outputs`

## [0.5.0] - 2024-07-17

- support python3.11
- support kedro ~=0.19.6

### DataSet and DataSetInput types

The following fields of the `DataSet` and `DataSetInput` types are marked for
deprecation and will be removed in a future release:

- `filepath`
- `load_args`
- `save_args`
- `type`

```
@strawberry.type
class DataSet:
    name: str
    config: Optional[str] = None
    type: Optional[str] = mark_deprecated(default = None)
    filepath: Optional[str] = mark_deprecated(default = None)
    save_args: Optional[List[Parameter]] = mark_deprecated(default = None)
    load_args: Optional[List[Parameter]] = mark_deprecated(default = None)
    credentials: Optional[str] = None
```

```
@strawberry.input
class DataSetInput:
    name: str
    config: Optional[str] = None
    type: Optional[str] = mark_deprecated(default = None)
    filepath: Optional[str] = mark_deprecated(default = None)
    save_args: Optional[List[ParameterInput]] = mark_deprecated(default = None)
    load_args: Optional[List[ParameterInput]] = mark_deprecated(default = None)
    credentials: Optional[str] = None
```

The `config` field should be used instead to specify a dataset configuration as a JSON
string.  The `config` field approach supports all dataset implementations.

### Pipeline and PipelineInput types

The following fields of the `Pipeline` and `PipelineInput` types are marked for
deprecation and will be removed in a future release:

- `inputs`
- `outputs`

```
@strawberry.type
class Pipeline:
    kedro_pipelines: strawberry.Private[Optional[dict]] = None
    kedro_catalog: strawberry.Private[Optional[dict]] = None
    kedro_parameters: strawberry.Private[Optional[dict]] = None

    id: Optional[uuid.UUID] = None
    inputs: Optional[List[DataSet]] = mark_deprecated(default= None)
    name: str
    outputs: Optional[List[DataSet]] = mark_deprecated(default= None)
    data_catalog: Optional[List[DataSet]] = None
    parameters: List[Parameter]
    status: Optional[str] = None
    tags: Optional[List[Tag]] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    task_args: Optional[str] = None
    task_kwargs: Optional[str] = None
    task_request: Optional[str] = None
    task_exception: Optional[str] = None
    task_traceback: Optional[str] = None
    task_einfo: Optional[str] = None
    task_result: Optional[str] = None
```

```
@strawberry.input(description = "PipelineInput")
class PipelineInput:
    name: str
    parameters: Optional[List[ParameterInput]] = None
    inputs: Optional[List[DataSetInput]] = mark_deprecated(default = None)
    outputs: Optional[List[DataSetInput]] = mark_deprecated(default = None)
    data_catalog: Optional[List[DataSetInput]] = None
    tags: Optional[List[TagInput]] = None
```

The `data_catalog` field should be used instead.
