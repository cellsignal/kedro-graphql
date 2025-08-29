# Changelog

## [Unreleased]

Added:

- command-line flags for all configuration options, including complex data types support using JSON strings
- proper configuration loading order (YAML spec > CLI flags > Environment variables > .env file > Defaults)
- support for comma-separated strings, JSON arrays, and single values for list-type configuration options
- `test_config.py` with unit tests for configuration precedence and data type parsing scenarios
- `root_path` configuration option to support API endpoint prefixing
- support for both `X-Forwarded-*` and `x-auth-request-*` header formats for OAuth2 proxy compatibility

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
