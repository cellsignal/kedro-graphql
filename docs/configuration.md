The following table describes each configuration attribute available:

| Attribute                              | Type | Default | Description                                                                                      |
|-----------------------------------------|------|---------|--------------------------------------------------------------------------------------------------|
| `app`                                  | string | `kedro_graphql.asgi.create_app` | Python path to the application factory.                                                    |
| `app_description`                      | string | `A tool for serving kedro projects as a GraphQL API` | Description of the Kedro GraphQL application.                                                    |
| `app_title`                            | string | `Kedro GraphQL API` | Title of the Kedro GraphQL application.                                                          |
| `backend`                              | string | `kedro_graphql.backends.mongodb.MongoBackend` | Python path to the backend class for data storage and retrieval.                                 |
| `broker`                               | string | `redis://localhost` | URI for the message broker (e.g., Redis) used for task queueing.                                |
| `celery_result_backend`                 | string | `redis://localhost` | URI for the Celery result backend (e.g., Redis).                                                 |
| `celery_abort_polling_interval`         | float | `5` | Polling interval in seconds used by abortable Celery tasks to check whether a running pipeline should be interrupted. Minimum value is `1` second (values below are clamped to `1`). |
| `celery_abort_grace_period`             | float | `60` | Grace period in seconds before escalating task abort signals (`SIGINT` -> `SIGTERM` -> `SIGKILL`). Minimum value is `5` seconds (values below are clamped to `5`). |
| `client_uri_graphql`                   | string | `http://localhost:5000/graphql` | URI for GraphQL API endpoint used by the GraphQL client.                                         |
| `client_uri_ws`                        | string | `ws://localhost:5000/graphql` | URI for WebSocket endpoint used by the GraphQL client for subscriptions.                         |
| `conf_source`                          | string | `None` | Optional path to an alternative configuration source.                                             |
| `dataset_filepath_masks`                  | list(dict) | [] | Masks to apply to Dataset filepaths before returning responses to client to hide true location of datasets (e.g. [{"prefix": "/tmp/", "mask": "/REDACTED/"}]) |
| `dataset_filepath_allowed_roots`                  | list | [] | Allow root prefixes for Dataset filepaths (e.g. ["/tmp/"]) |
| `deprecations_docs`                     | string | `""` | Optional URL to documentation about deprecated features.                                          |
| `env`                                  | string | `local` | Environment name (e.g., "local").                                                                |
| `events_config`                        | dict | `None` | Dictionary for event configuration. Specify as JSON string when using CLI/environment variables. |
| `imports`                              | list | `["kedro_graphql.plugins.plugins"]` | List of Python modules to import for plugin registration. Can be specified as comma-separated string or JSON array. |
| `local_file_provider_download_allowed_roots` | list | `["./data", "/var", "/tmp"]` | List of allowed root directories for downloads. Can be specified as comma-separated string or JSON array. |
| `local_file_provider_jwt_algorithm`    | string | `HS256` | Algorithm used for JWT signing.                                                |
| `local_file_provider_jwt_secret_key`   | string | `my-secret-key` | Secret key for signing JWT tokens for local file access.                                        |
| `local_file_provider_server_url`       | string | `http://localhost:5000` | Base URL for the local file server.                             |
| `local_file_provider_upload_allowed_roots`   | list | `["./data"]` | List of allowed root directories for uploads. Can be specified as comma-separated string or JSON array. |
| `local_file_provider_upload_max_file_size_mb` | integer | `10` | Maximum allowed upload file size in megabytes. |
| `log_path_prefix`                      | string | `None` | Persistent local directory or S3 prefix for worker-owned `runs/<pipeline-id>/<task-id>/manifest.json` and `events.jsonl`. |
| `log_tmp_dir`                          | string | `tempfile.TemporaryDirectory().name` | Local task log spool and recovery files. Use persistent storage when worker replacement must preserve failed uploads. |
| `mongo_db_collection`                   | string | `pipelines` | Name of the MongoDB collection to use.                                                           |
| `mongo_db_name`                        | string | `pipelines` | Name of the MongoDB database to use.                                                             |
| `mongo_indexes`                        | list | `[]` | Application-owned Mongo index definitions; provision explicitly with `kedro gql mongo-indexes --apply`. |
| `mongo_uri`                            | string | `mongodb://root:example@localhost:27017/` | MongoDB connection URI string.                                                                   |
| `permissions`                          | string | `kedro_graphql.permissions.IsAuthenticatedAlways` | Python path to the permissions class used for authentication.                                    |
| `permissions_group_to_role_map`        | dict | `{"EXTERNAL_GROUP_NAME": "admin"}` | Mapping of external group names to roles. Specify as JSON string when using CLI/environment variables. |
| `permissions_role_to_action_map`       | dict | `{"admin": [...]}` | Mapping of roles to allowed actions. Specify as JSON string when using CLI/environment variables. |
| `pipeline_config_sources`              | dict | `{}` | Required allowlist mapping API pipeline names to runtime-mounted Kedro configuration directories. |
| `pipeline_submission_max_bytes`        | integer | `1048576` | Maximum UTF-8 JSON size of the resolved catalog and parameters. Configure through YAML or `KEDRO_GRAPHQL_PIPELINE_SUBMISSION_MAX_BYTES`. |
| `pipeline_submission_parameter_allowlists` | dict | `{}` | Per-pipeline lists of parameter paths shown as submission form controls. An omitted pipeline entry allows all paths; an empty list allows none. |
| `pipeline_submission_parameter_disallowlists` | dict | `{}` | Per-pipeline lists of parameter paths hidden from submission form controls. The deepest matching rule wins; disallow wins ties. |
| `project_version`                      | string | `None` | Version of the Kedro GraphQL project.                                                            |
| `root_path`                            | string | `""` | Root path for all API endpoints (e.g., '/api/v1'). When set, all API routes will be prefixed with this path. |
| `pipeline_runners` | dict | `{}` | Server-owned mapping of pipeline names to runner class paths. Takes precedence over an input runner; unmapped pipelines use the input runner or `runner`. |
| `runner`                               | string | `kedro.runner.SequentialRunner` | Python path to the Kedro runner class.                                                           |
| `signed_url_max_expires_in_sec`    | integer | `43200` | Maximum allowed expiration time (in seconds) for presigned URLs. Default: 12 hours. |
| `signed_url_provider`                  | string | `kedro_graphql.signed_url.s3_provider.S3Provider` | Python path to the presigned URL provider class (e.g., for S3 or local file support). |

External runners that outlive the Celery worker should also inherit
`kedro_graphql.runners.ExternalRunnerLifecycle`. Implement `terminate()` to
request external cancellation and `reconcile()` to inspect the external system
and return a confirmed `kedro_graphql.models.State`, or `None` while no state
change is confirmed. Both methods receive the same `run_context` and
`emit_metadata` attributes as `run()`. The context contains `pipeline_id`,
`task_id`, and persisted `x-` metadata. Reads reconcile the stored state;
aborts and deletes request termination and retain the pipeline in `ABORTING`
until `reconcile()` confirms `ABORTED`.

Before `run()`, external runners also receive `remote_hook_specs`, a list of
serializable selected entry-point references containing `name`, `module`,
`attribute`, and node/dataset callback names. The external execution image can
load these specs with a standalone Kedro hook loader; it does not need to
install `kedro-graphql`.

Resolved pipeline configuration may contain a named credential reference such
as `credentials: production-s3`, but not an inline credentials mapping or
fields such as `password`, `token`, `api_key`, `secret_key`, or AWS access-key
values. Supply secrets through the referenced Kedro credential provider or
workload identity. The API rejects configuration larger than
`pipeline_submission_max_bytes` before persistence or task publication.


Configuration can be supplied through one or more of the following methods:

- [YAML API Spec](#yaml-api-specification)
- [command line](#command-line)
- [environment](#environment)
- ```.env``` file

## Data Types and Formats

Kedro GraphQL supports flexible configuration formats for different data types:

Simple string values can be provided directly:

```bash
--app-title "My Custom App"
--mongo-uri "mongodb://localhost:27017/"
```

Numeric values are automatically converted:

```bash
--signed-url-max-expires-in-sec 3600
--local-file-provider-upload-max-file-size-mb 50
```

List-type configuration options support multiple input formats:

**Comma-separated strings:**

```bash
--imports "module1.plugin,module2.plugin,module3.plugin"
--local-file-provider-download-allowed-roots "./data,/var,/tmp"
```

**JSON arrays:**

```bash
--imports '["module1.plugin", "module2.plugin"]'
--local-file-provider-download-allowed-roots '["./data", "/var", "/tmp"]'
```

**Single values (automatically converted to list):**

```bash
--imports "single.module"
--local-file-provider-upload-allowed-roots "./uploads"
```

Complex dictionary configurations must be provided as JSON strings:

```bash
--events-config '{"event1": {"source": "app", "type": "test"}}'
--permissions-role-to-action-map '{"admin": ["create_pipeline", "read_pipeline"]}'
```

When using environment variables, list and dictionary values should be provided as:

- **Lists**: Comma-separated strings or JSON arrays
- **Dictionaries**: JSON strings

```bash
export KEDRO_GRAPHQL_IMPORTS="module1,module2,module3"
export KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS='["./data", "/tmp"]'
export KEDRO_GRAPHQL_EVENTS_CONFIG='{"event1": {"source": "app"}}'
export KEDRO_GRAPHQL_PIPELINE_CONFIG_SOURCES='{"example00": "/runtime/pipelines/example00"}'
```

## Configuration Precedence

Configuration values are loaded with the following precedence order (highest to lowest):

1. **YAML Spec** (highest precedence) - Values specified in the YAML spec file passed via `--api-spec` or `--ui-spec`
2. **Command Line Flags** - Values passed as CLI arguments to the `kedro gql` command
3. **Environment Variables** - Values set as environment variables with `KEDRO_GRAPHQL_` prefix
4. **.env File** - Values defined in a `.env` file in the project root
5. **Defaults** (lowest precedence) - Built-in default values

This means that if the same configuration option is specified in multiple places, the source with higher precedence will override those with lower precedence. For example, a value in the YAML spec will override the same value specified via CLI flags, environment variables, or defaults.

## YAML API Specification

The YAML API uses a snake case format without the `KEDRO_GRAPHQL_` prefix. In YAML specs, you can use native YAML data types (lists, dictionaries) directly.

### Basic YAML Configuration Example

```yaml
## Kedro GraphQL YAML API configuration file.
config:
  app: "kedro_graphql.asgi.create_app"
  app_description: "A tool for serving kedro projects as a GraphQL API"
  app_title: "Kedro GraphQL"
  backend: "kedro_graphql.backends.mongodb.MongoBackend"
  broker: "redis://localhost"
  celery_result_backend: "redis://localhost"
  celery_abort_polling_interval: 5
  celery_abort_grace_period: 60
  client_uri_graphql: "http://localhost:5000/graphql"
  client_uri_ws: "ws://localhost:5000/graphql"
  conf_source: null
  deprecations_docs: ""
  env: "local"
  events_config:
    event00:
      source: "example.com"
      type: "com.example.event"
    event01:
      source: "api.service.com"
      type: "com.service.notification"
  imports:
    - "kedro_graphql.plugins.plugins"
    - "custom.plugins"
  local_file_provider_download_allowed_roots:
    - "./data"
    - "/var"
    - "/tmp"
  local_file_provider_jwt_algorithm: "HS256"
  local_file_provider_jwt_secret_key: "my-secret-key"
  local_file_provider_server_url: "http://localhost:5000"
  local_file_provider_upload_allowed_roots:
    - "./data"
    - "./uploads"
  local_file_provider_upload_max_file_size_mb: 10
  log_path_prefix: null
  log_tmp_dir: "/tmp/"
  mongo_db_collection: "pipelines"
  mongo_db_name: "pipelines"
  mongo_uri: "mongodb://root:example@localhost:27017/"
  permissions: "kedro_graphql.permissions.IsAuthenticatedXForwardedEmail"
  permissions_group_to_role_map: 
    EXTERNAL_ADMIN_GROUP: admin
    EXTERNAL_VIEWER_GROUP: viewer
  permissions_role_to_action_map:
    admin:
      - "create_pipeline"
      - "read_pipeline"
      - "read_pipelines"
      - "update_pipeline"
      - "delete_pipeline"
      - "read_pipeline_template"
      - "read_pipeline_templates"
      - "create_dataset"
      - "read_dataset"
      - "subscribe_to_events"
      - "subscribe_to_logs"
      - "create_event"
    viewer:
      - "read_pipeline"
      - "read_pipelines"
      - "read_dataset"
  pipeline_config_sources:
    example00: /runtime/pipelines/example00
  pipeline_submission_max_bytes: 1048576
  project_version: "1.0.1"
  root_path: null
  runner: "kedro.runner.SequentialRunner"
  signed_url_max_expires_in_sec: 43200
  signed_url_provider: "kedro_graphql.signed_url.s3_provider.S3Provider"
```

### Using the API Spec

Use the `--api-spec` flag to specify the path to the configuration file:

```bash
kedro gql --api-spec spec-api.yaml
```

## Command line

The configuration can also be provided at startup through the cli interface.
Configuration values can be mapped to the the appropriate cli option by
removing the `KEDRO_GRAPHQL_` prefix and using a lower case, hyphen format
for the remaining string. For complex data types (lists, dictionaries),
provide them as JSON strings.

| configuration attribute                              | cli option                                       | example                                              |
|----------------------------------------------------|--------------------------------------------------|------------------------------------------------------|
| app                                                | --app                                            | kedro_graphql.asgi.create_app                      |
| app_title                                          | --app-title                                      | "My Custom Kedro GraphQL"                           |
| app_description                                    | --app-description                                | "Custom description"                                 |
| dataset_filepath_masks                             | --dataset-filepath-masks                         | `[{"prefix": "/tmp/", "mask": "/REDACTED/"}]`     |
| dataset_filepath_allowed_roots                     | --dataset-filepath-allowed-roots                          | `["/tmp/"]`     |
| backend                                            | --backend                                        | kedro_graphql.backends.mongodb.MongoBackend         |
| broker                                             | --broker                                         | redis://localhost                                    |
| celery_result_backend                              | --celery-result-backend                          | redis://localhost                                    |
| celery_abort_polling_interval                      | --celery-abort-polling-interval                  | 5                                                    |
| celery_abort_grace_period                          | --celery-abort-grace-period                      | 60                                                   |
| client_uri_graphql                                 | --client-uri-graphql                             | http://localhost:5000/graphql                        |
| client_uri_ws                                      | --client-uri-ws                                  | ws://localhost:5000/graphql                          |
| conf_source                                        | --conf-source                                    | $HOME/myproject/conf                                 |
| deprecations_docs                                  | --deprecations-docs                              | `https://github.com/myrepo/docs` (optional)         |
| env                                                | --env                                            | local                                                |
| events_config                                      | --events-config                                  | '{"event1": {"source": "app", "type": "test"}}'     |
| imports                                            | --imports                                        | `kedro_graphql.plugins.plugins` or `["module1", "module2"]` |
| local_file_provider_download_allowed_roots         | --local-file-provider-download-allowed-roots    | `./data,/var,/tmp` or `["./data", "/var", "/tmp"]`   |
| local_file_provider_jwt_algorithm                  | --local-file-provider-jwt-algorithm             | HS256                                                |
| local_file_provider_jwt_secret_key                 | --local-file-provider-jwt-secret-key            | my-secret-key                                        |
| local_file_provider_server_url                     | --local-file-provider-server-url                | `http://localhost:5000`                              |
| local_file_provider_upload_allowed_roots           | --local-file-provider-upload-allowed-roots      | `./data` or `["./data"]`                             |
| local_file_provider_upload_max_file_size_mb        | --local-file-provider-upload-max-file-size-mb   | 10                                                   |
| log_path_prefix                                    | --log-path-prefix                                | s3://my-bucket/                                      |
| log_tmp_dir                                        | --log-tmp-dir                                    | my_tmp_dir/                                          |
| mongo_db_collection                                | --mongo-db-collection                            | pipelines                                            |
| mongo_db_name                                      | --mongo-db-name                                  | pipelines                                            |
| mongo_uri                                          | --mongo-uri                                      | mongodb://root:example@localhost:27017/              |
| permissions                                        | --permissions                                    | kedro_graphql.permissions.IsAuthenticatedAlways     |
| permissions_group_to_role_map                      | --permissions-group-to-role-map                 | '{"EXTERNAL_GROUP_NAME": "admin"}'                  |
| permissions_role_to_action_map                     | --permissions-role-to-action-map                | '{"admin": ["create_pipeline", "read_pipeline"]}'    |
| project_version                                    | --project-version                                | 1.0.0                                                |
| root_path                                          | --root-path                                      | /api/v1                                              |
| runner                                             | --runner                                         | kedro.runner.SequentialRunner                       |
| signed_url_max_expires_in_sec                      | --signed-url-max-expires-in-sec                  | 43200                                                |
| signed_url_provider                                | --signed-url-provider                            | kedro_graphql.signed_url.s3_provider.S3Provider     |

**Note:** For complex data types (lists, dictionaries), provide values as JSON strings. The system will automatically parse these JSON strings into the appropriate data structures.

### CLI Examples

**Basic usage:**

```bash
kedro gql --app-title "My Custom App" --mongo-uri "mongodb://localhost:27017/"
```

**Using JSON for complex data types:**

```bash
kedro gql --permissions-role-to-action-map '{"admin": ["create_pipeline", "read_pipeline"]}' \
          --local-file-provider-download-allowed-roots '["./data", "/var", "/tmp"]'
```

**Different ways to specify imports:**

```bash
# Comma-separated string
kedro gql --imports "module1.plugin,module2.plugin,module3.plugin"

# JSON array
kedro gql --imports '["module1.plugin", "module2.plugin"]'

# Single module (automatically converted to list)
kedro gql --imports "single.module"
```

**Different ways to specify file paths:**

```bash
# Comma-separated strings for file paths
kedro gql --local-file-provider-download-allowed-roots "./data,/var,/tmp" \
          --local-file-provider-upload-allowed-roots "./uploads,./data"

# JSON arrays for file paths
kedro gql --local-file-provider-download-allowed-roots '["./data", "/var", "/tmp"]' \
          --local-file-provider-upload-allowed-roots '["./uploads", "./data"]'

# Single paths (automatically converted to list)
kedro gql --local-file-provider-upload-allowed-roots "./uploads"
```

## Environment

Environment variables will take precedence over values defined in a `.env` file. When using environment variables, the configuration attribute name should be uppercase and prefixed with `KEDRO_GRAPHQL_`.

### Environment Variable Format Examples

**String values:**

```bash
KEDRO_GRAPHQL_MONGO_URI=mongodb://root:example@localhost:27017/
KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL=http://localhost:5000/graphql
KEDRO_GRAPHQL_CLIENT_URI_WS=ws://localhost:5000/graphql
KEDRO_GRAPHQL_CELERY_ABORT_POLLING_INTERVAL=5
KEDRO_GRAPHQL_CELERY_ABORT_GRACE_PERIOD=60
KEDRO_GRAPHQL_APP_TITLE="My Custom Kedro GraphQL"
KEDRO_GRAPHQL_BACKEND=kedro_graphql.backends.mongodb.MongoBackend
```

**List values (multiple formats supported):**

```bash
# Comma-separated strings
KEDRO_GRAPHQL_IMPORTS=kedro_graphql.plugins.plugins,custom.plugin
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS=./data,/var,/tmp

# JSON arrays
KEDRO_GRAPHQL_IMPORTS='["kedro_graphql.plugins.plugins", "custom.plugin"]'
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS='["./data", "./uploads"]'
```

**Dictionary values (JSON format required):**

```bash
KEDRO_GRAPHQL_EVENTS_CONFIG='{"event1": {"source": "app", "type": "test"}}'
KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP='{"admin": ["create_pipeline", "read_pipeline"]}'
```

## Live pipeline status

`pipelineUpdates(id)` sends persisted run history and dataset existence, initially
and whenever they change. Mongo is authoritative for run state; existence is
checked in storage. Checks run every two seconds while active and once at the
end of a run. Failed existence checks return null. The subscription requires
`read_pipeline` and `subscribe_to_events`; it remains open for subsequent runs.
API startup also starts external-run reconciliation every five seconds, using
the shared runner lifecycle and conditional Mongo updates independently of clients.

`pipelineSubmissionForm` includes the effective server-selected `runner` for review
before submission. `pipeline_submission_upload_roots` maps pipeline names to
upload roots, taking precedence over `pipeline_submission_upload_root`; this
allows remote-runner uploads to use S3 alongside local-runner uploads.


## Submission parameter visibility

Configure parameter visibility by pipeline name in the API spec:

```yaml
config:
  pipeline_submission_parameter_allowlists:
    example_pipeline:
      - settings
      - enabled
      - settings.internal.threshold
  pipeline_submission_parameter_disallowlists:
    example_pipeline:
      - settings.internal
```

Paths use dot notation and match the named parameter and its entire subtree.
Here, `settings` and `enabled` are allowed, `settings.internal` is hidden,
and the more specific allow rule exposes `settings.internal.threshold` again.
A more specific disallow rule would hide a child of an allowed subtree.
If the same exact path appears in both lists, disallow wins. List order does not
matter, and `settings` does not match `settings_extra`.

Without an allowlist entry for a pipeline, all its form parameters start visible.
An explicit empty allowlist hides all parameter controls. The submission form API
returns every parameter for the selected graph, with `visibleInForm` indicating
which controls the UI should show. Hidden parameters remain visible with their
defaults on the confirmation page and with their resolved values on the pipeline
page. The UI omits hidden parameters from submitted overrides. These rules also
hide read-only form rows. Arrays remain
whole values; paths do not address individual array elements.

Hidden parameters retain their server defaults when omitted. A hidden required
parameter without a server default makes form generation fail with the pipeline
name and parameter path. Null, false, zero, and empty collections are valid
defaults. These settings control UI visibility, not API permissions: explicit
API overrides of hidden parameters still undergo the existing validation and
remain accepted when valid.

Environment values use JSON mappings through
`KEDRO_GRAPHQL_PIPELINE_SUBMISSION_PARAMETER_ALLOWLISTS` and
`KEDRO_GRAPHQL_PIPELINE_SUBMISSION_PARAMETER_DISALLOWLISTS`, for example:

```bash
KEDRO_GRAPHQL_PIPELINE_SUBMISSION_PARAMETER_ALLOWLISTS='{"example_pipeline":["settings","enabled"]}'
KEDRO_GRAPHQL_PIPELINE_SUBMISSION_PARAMETER_DISALLOWLISTS='{"example_pipeline":["settings.internal"]}'
```

## UI batch submission limits

`pipeline_submission_batch_max_size` defaults to 10. Set
`pipeline_submission_batch_max_sizes` to a mapping of pipeline names to positive
integer limits to override it for individual pipelines. Both settings use the
existing API-spec/environment configuration loader; the environment mapping is JSON.

The submission form exposes `maxBatchSize` and `batchLimitReason`. These are UI
limits, not resource quotas: the UI validates all entries, then calls the existing
single-pipeline submission API for each entry. Persistent outputs without a
server-managed `filepath` or `path` restrict the form to one entry.

Server-managed paths are scoped by pipeline ID for every produced catalog dataset,
including intermediate datasets. Free input locations remain shared. Node side
effects outside the Data Catalog are not isolated by this mechanism.

## Dataset input autocomplete

`dataset_input_providers` registers application providers by Python import path,
required `pipeline_name` and `dataset_name`, and an `options` mapping passed as
constructor keyword arguments. The framework matches both names before calling
provider eligibility or search methods. Each registration serves one input;
other inputs cannot invoke it, even through direct GraphQL queries. Providers
inherit `kedro_graphql.autocomplete.DatasetInputProvider`, identify their input
`method`, and implement cheap `supports(context)` and blocking
`search(context, query, limit)` methods. Context contains pipeline/dataset names,
server catalog configuration, slices, and caller identity (absent during form
discovery). Eligibility must not depend on caller identity; search must enforce
caller access where required. Search returns `InputSuggestions` with
`InputSuggestion(label, value)` entries and a `truncated` flag. Values are JSON;
consumers map them to the advertised existing input method.

Providers may override `resolve(context, value)` to expand an application value to a storage location before standard S3 scope and location validation; the default returns the supplied location unchanged.

Providers are loaded once at application startup. No providers are registered
by default. Overlapping registrations for the same input are an error. The
submission form exposes nullable `autocomplete { method }`; the query
`datasetInputSuggestions(name, datasetName, slices, query, limit)` checks the
selected free input and both template-read and dataset-read permissions. Limit defaults to 10 and must
be 1–50. Search requires two characters. Searches run in a thread pool; errors
do not change pipeline state or submission validation.

### Multiple-file collection inputs

A dataset class may advertise `submission_input_location_key = "paths"`.
Subclasses inherit this capability. The submission form reports `kind: COLLECTION`
and accepts `S3_URI` inputs containing a nonempty `s3Uris` list rather than
`s3Uri`. Each URI is scope/access validated; duplicate URIs and scalar/list
shape mismatches are rejected. The resolved catalog receives `paths: [...]`
while retaining its original dataset type, nested dataset configuration, and
other options. Collection uploads are not exposed by this submission form.
Dataset constructors retain their own format/protocol restrictions. Ordinary
partitioned inputs use a directory prefix or folder upload rather than a list of file URIs.

### Submission output directories

`pipeline_submission_output_roots` maps pipeline names to an output root.
All managed outputs for a configured pipeline share `<root>/<pipeline-id>/`;
single files retain their basename and partitioned datasets write their partitions
directly into that directory. Output filenames must be distinct across datasets.

### Application submission transformation

`pipeline_submission_transforms` maps pipeline names to dotted Python callables.
Only submissions for a listed pipeline invoke its transform; unlisted pipelines
receive no transformation. For example:

```yaml
pipeline_submission_transforms:
  xmt_abp_qc: molbio.submission.prepare_submission
```

The API calls the selected transform after validating frontend inputs and parameters, before constructing
or persisting a pipeline, for both validation and submission. Its signature is
`transform(pipeline_input, merged_parameters, managed_outputs)` and it returns
`(pipeline_input, managed_outputs)`. Applications can set run-specific globals
and runner parameters here. Return an empty managed-output list when the
application already assigns an isolated directory for the entire run. Raise
`InvalidPipeline` or `ValueError` for invalid application inputs. Validation
must not write data or launch work; transformations may generate a fresh run ID.

### Archived log reads

`pipelineArchivedLogs(id, before, maxBytes)` reads the latest saved execution
attempt under `log_path_prefix/runs/<pipeline-id>/<task-id>/events.jsonl`.
It requires `read_pipeline` and `subscribe_to_logs` permissions. The client
cannot supply a storage path. Completed attempts (success, failure, aborted,
or revoked) return an `ArchivedLogChunk` with `availability`, `taskId`, `text`,
`earlierCursor`, `skippedContent`, and an optional user-facing `message`.

The first request reads the final 64 KiB; `maxBytes` accepts 1–262144 bytes.
Pass `earlierCursor` as `before` to read the preceding chunk. Cursors are bound
to both pipeline and latest task ID; reopening the view is required after an
attempt changes. Reads preserve complete JSONL records where possible; damaged
or oversized records are skipped with `skippedContent=true`. Empty archives
are available with empty text. Missing or unconfigured archives are
`UNAVAILABLE`, and storage failures are `UNREADABLE`; callers may retry.
Local and S3 paths use the existing fsspec filesystem support and API-process
credentials. Local archives must be shared with the API; remote archive reads
require object-read permission. This query does not change archive creation or
migrate historical logs stored in a different format.

## Mongo index provisioning

Applications own their index definitions. `mongo_indexes` defaults to an empty
list; neither API startup nor workers create these indexes automatically.

```yaml
config:
  mongo_indexes:
    - keys: [[created_at, -1], [_id, -1]]
      name: created_at_-1__id_-1
    - collection: fastq_files
      keys: [[uri, 1]]
      name: uri_1
      unique: true
```

`keys` is an ordered list of field/direction pairs. `collection` is optional and
uses `mongo_db_collection` when omitted. All remaining fields are passed directly
to PyMongo's `IndexModel`, including `name`, `unique`, `partialFilterExpression`,
`expireAfterSeconds`, and `collation`. Mongo validates supported index types and
options; the application does not maintain a separate Mongo option schema.
The same list can be supplied as JSON in `KEDRO_GRAPHQL_MONGO_INDEXES`, using the
existing configuration precedence. No additional connection settings are needed.

Run from the application's Kedro project with its normal Mongo environment:

```bash
kedro gql --api-spec /path/to/api-spec.yaml mongo-indexes
kedro gql --api-spec /path/to/api-spec.yaml mongo-indexes --apply
```

The first command lists current indexes for configured collections, or the
pipeline collection if no indexes are configured. It performs no writes and is
not a drift comparison. `--apply` creates the declared indexes; an empty list is
a no-op. Reapplying matching definitions leaves existing indexes unchanged.
Conflicts fail with a nonzero exit code and Mongo's error code. Other indexes
are untouched, including definitions removed from configuration. Changes that
require dropping an index must be handled as an explicit database migration.
Application across collections is not transactional: earlier successful creations
can remain after an error. Always provision before starting writers that depend
on uniqueness constraints. Indexes alone do not make unanchored, case-insensitive
substring searches efficient; query changes are a separate concern.

## Partitioned submission inputs

`pipelineSubmissionForm` supports `PartitionedDataset`, `IncrementalDataset`, and
subclasses, including fully qualified catalog type names. Supply an S3 directory
prefix or upload a folder; the server retains the dataset's other catalog settings.
S3 prefixes accept an omitted trailing slash and must fall within
`pipeline_submission_s3_allowed_prefixes`. A bucket root is allowed only when the
configured scope includes that bucket root. Prefix boundaries exclude sibling
names such as `input-other` when the allowed scope is `input`.

Validation requires at least one actual file matching the catalog's
`filename_suffix` (an empty suffix accepts any file). Incremental inputs must
contain a partition eligible after checkpoint filtering. Discovery uses Kedro's
settings without loading partition contents or advancing checkpoints, and runs
again before submission. Storage and checkpoints can still change before execution.

`createPipelineSubmissionFolderUpload` accepts the pipeline, free input, selected
slices, and `files: [{relativePath, size}]`. Byte sizes use GraphQL `Float` because
GraphQL `Int` is limited to signed 32-bit values. The result contains one bundle
`uploadId` and per-file upload instructions. Upload each file, then use the bundle
ID in the existing `UPLOAD` submission input. Relative paths preserve subfolders;
absolute paths, traversal, duplicates, and invalid sizes are rejected. All declared
files must exist with their declared sizes before the folder can be submitted.
Local files are published atomically after a complete transfer.

Folder limits are configured centrally:

- `pipeline_submission_partition_upload_max_files`: 1,000 by default.
- `pipeline_submission_partition_upload_max_size_mb`: 1,024 MiB total by default.
- `local_file_provider_upload_max_file_size_mb`: the existing per-file limit
  (10 MiB by default).
- `pipeline_submission_upload_expires_in_sec`: the existing upload expiry.

The browser selects folders directly, strips the chosen top-level folder name,
and uploads all files while preserving nested paths. No ZIP archive is required.
Use an existing S3 prefix for folders exceeding browser upload limits. Upload
expiry invalidates signing tokens; it does not delete stored files or introduce
cleanup of abandoned uploads. API and worker processes using local uploads must
share the upload filesystem and have permission to read the files.

## Derived dataset submission inputs

Declare suffix appending, suffix replacement, or Python regex substitution in API configuration:

```yaml
config:
  dataset_input_derivations:
    - pipeline_name: analysis
      dataset_name: full.bam_index
      source_dataset: full.bam
      append_suffix: .bai
```

Use exactly one operation per rule. For replacement, declare the suffix to match
and its replacement explicitly:

```yaml
config:
  dataset_input_derivations:
    - pipeline_name: analysis
      dataset_name: full.bam_index
      source_dataset: full.bam
      replace_suffix:
        from_suffix: .bam
        to_suffix: .bai
```

This maps `sample.bam` to `sample.bai`. Matching is case-sensitive and applies
only at the end of the filename. Compound suffixes such as `.bam.gz` are supported;
a source that does not match is rejected under the target input. Directory names
and earlier occurrences are retained. CSTEP-I keeps its append rules because its
indexes use `sample.bam.bai`.

Derivation models and dependency validation live in
`kedro_graphql.dataset_input_derivations`; configuration loading invokes them.
Registrations require nonempty names and nonempty filename suffixes. Duplicate
pipeline/target pairs, self-references, cycles, unknown exposed
pipelines, and unknown graph datasets are rejected. Sources and targets must be
single-file datasets when the rule applies. Independent pipelines may use the
same target name.

Acyclic chains are supported and resolved in dependency order, regardless of
registration order. An explicit override of an intermediate dataset becomes the
source for its downstream derivations. For CSTEP-I, `full.bam_index` appends
`.bai` to `full.bam`; `dedup.bam` and `dedup.bam_index` replace `full` with
`dedup` in `full.bam` and `full.bam_index`, respectively.

The form advertises `inputs.derivation { sourceDataset appendSuffix replaceSuffix { fromSuffix toSuffix } regexSub { pattern replacement } }` only when
both datasets are external inputs of the selected slice. A dataset produced by
the selected slice is never replaced. If the target is external but its source
is produced by the slice or absent from its inputs, supply the target explicitly.

When the source uses `S3_URI`, omit the target to use derivation, or supply an
explicit target to override the rule. An append rule appends the
suffix to the entire object URI (`sample.bam` becomes `sample.bam.bai`). All
operations run the existing scope and S3 HEAD checks on both objects. Explicit
targets bypass derivation and use normal dataset validation, including S3 scopes
or upload-token checks; they can override a replacement rule even if the source
does not match its configured suffix. Validation and submission use the same resolution and populate
both existing catalog entries with concrete locations. Neither the Kedro graph
nor the stored pipeline model changes.

`validatePipelineSubmission` returns `resolvedInputs { name s3Uri }` for derived
candidates, including candidates that fail accessibility checks; the associated
error remains in `errors` under the target dataset's name. The UI defaults to derivation, showing the resolved target read-only. Turn off
"Derive from" to use the regular S3 or upload controls. Turning derivation back
on clears the previous derived result and validates again. Source changes clear
only automatic target results; explicit targets remain independent.
CSV templates include optional target columns: blank or omitted values derive,
while filled values override the rule for that row. Every row is validated and
both automatic and explicit paths appear in the report and confirmation.

Derivation is initially S3-only. Uploaded sources retain explicit target inputs,
which may use the existing S3 or upload methods. Checking accessibility does not
prove that a BAM index matches its BAM, and files may change after validation.

### Python regex derivations

Choose exactly one of `append_suffix`, `replace_suffix`, or `regex_sub` per rule:

```yaml
config:
  dataset_input_derivations:
    - pipeline_name: analysis
      dataset_name: full.bam_index
      source_dataset: full.bam
      regex_sub:
        pattern: '(?P<stem>[^/]+)\.bam$'
        replacement: '\g<stem>.bai'
```

The backend calls Python `re.sub(pattern, replacement, source_uri)` on the entire
S3 URI. Python capture groups, named references, and inline flags such as `(?i)`
are supported; all matches are replaced. An empty replacement is allowed. If the
pattern does not match, the URI is unchanged, following Python's standard behavior.
Use YAML single quotes to preserve backslashes. Invalid patterns or replacement
references are rejected when configuration loads.

The resulting URI must still pass the existing S3 URI, allowed-scope, and
accessibility checks. Explicit targets bypass the regex rule and receive normal
dataset validation. The browser displays backend-resolved paths without applying
JavaScript regex rules.

### Pipeline name visibility

Use the same exact-name policy for submission choices and pipeline search:

```yaml
config:
  pipeline_name_allowlist:
    - analysis
    - prepare_reads
  pipeline_name_disallowlist:
    - prepare_reads
```

With this example, only `analysis` is available for submission and visible in
pipeline search. An omitted allowlist starts with all pipeline names; an empty
allowlist permits none. Disallow removes names from that working set and wins
when a name appears in both lists. Matching is exact, without regex or wildcards.
Environment equivalents are `KEDRO_GRAPHQL_PIPELINE_NAME_ALLOWLIST` and
`KEDRO_GRAPHQL_PIPELINE_NAME_DISALLOWLIST`; use JSON arrays or comma-separated names.

The backend filters templates and search before pagination and rejects direct
submission attempts for excluded names. Existing records are retained and remain
accessible by ID; this setting controls visibility and submission, not record
access permissions. Search includes historical names unless the policy excludes
them, independently of the pipelines currently configured for submission.

## Catalog search

The shared API provides two independent connections accepting `CatalogSearchInput`:
`searchCatalogPipelines(search:, limit: 10, cursor:)` and
`searchCatalogDatasets(search:, limit: 50, cursor:)`. Clients can request them
concurrently and render either table without waiting for the other. Both require
`read_pipelines` and `read_dataset`, apply pipeline-name visibility, and mask all
configured locations in returned catalogs. General `readPipelines` remains available.

```graphql
query {
  searchCatalogPipelines(search: {text: "12345"}, limit: 10) {
    pipelines { id name createdAt tags { key value } }
    pageMeta { nextCursor }
  }
  searchCatalogDatasets(search: {text: "12345", datasetName: "full.bam"}, limit: 50) {
    datasets { dataset { name config } pipelineId pipelineName catalogIndex }
    pageMeta { nextCursor }
  }
}
```

Text is a literal case-insensitive substring of pipeline tag values or configured
`filepath`, `path`, and string entries in `paths`. File names match as part of those
locations. The main text does not search logical dataset names, pipeline
names/descriptions, or dataset tags. Partition prefixes are searched without listing partition files.
A pipeline matches a tag or any dataset location. A dataset matches its parent
pipeline's tag or its own location. The optional `datasetName` filter then narrows
these dataset rows by literal case-insensitive substring of their logical name,
before sorting and pagination. It does not affect pipeline inclusion. Optional `pipelineId`
is an exact Mongo ObjectId filter. Empty text with an ID returns the pipeline and
its datasets. Otherwise text must contain at least three trimmed characters.

Pipeline ordering is created date descending then ID descending; datasets sort by
normalized logical name, pipeline ID, and catalog position ascending. Duplicate
names retain distinct catalog positions. Each page accepts 1–200 rows and exposes
only a next cursor, not an exact total. Pass cursors unchanged; query expansion,
filters, tag keys, visibility, and masks are included in their fingerprint.
Catalog changes during selection return a retry error; pages are not snapshots.

### App-specific configuration

`catalog_search_tag_keys` selects searchable pipeline tag keys: omitted means all,
an explicit list restricts them, and an empty list searches only locations.
`catalog_search_term_expander` optionally names a synchronous Python callable that
accepts trimmed text and returns a list of equivalent text strings. The original
text is always included. This hook returns no Mongo predicates, performs no storage
lookup, and is limited to 20 distinct terms of at most 1024 characters each.
CSTEP-I uses this hook to include canonical L-prefixed and bare barcode digits;
the shared API owns the matching algorithm and permission rules.

### Stored projection and maintenance

The optional internal `dataset_search` field has version `2`, normalized catalog
entries (`catalog_index`, `name_folded`, `type_folded`, `type_short_folded`,
`locations_folded`), and `pipeline_tags` entries (`key`, `value_folded`). All Mongo
create, update, and conditional-update writers use the same document builder and
persist the projection from the exact catalog and tags being written. Failed
projection building logs a warning and removes stale enrichment in the same update
without blocking valid pipeline persistence. Public readers strip this field.

Missing or unsupported projection versions are processed from their catalog and
tags using the current matching rules. This permits existing on-disk records to
remain searchable without retaining superseded query modes. Version-2 candidate
queries use normalized fields; full catalogs are fetched only for selected records.
Candidate selection retains at most one extra row per page. Existing unprocessed
records and unanchored substring queries can still require significant scanning.
The whole database search is bounded by `dataset_search_timeout_seconds` (default
10), its environment variable `KEDRO_GRAPHQL_DATASET_SEARCH_TIMEOUT_SECONDS`, or
CLI `--dataset-search-timeout-seconds`. Timeouts return an explicit error, never a
partial page presented as complete. Narrow text or supply a pipeline ID.

Declare indexes through `mongo_indexes`, including separate multikey indexes for
`dataset_search.pipeline_tags.value_folded` and
`dataset_search.datasets.locations_folded`. Do not combine the independent tag
and dataset arrays in one compound index. The version index helps find unprocessed
records; dataset name/type indexes can support other catalog queries. Substring
matching is not guaranteed to be selective: inspect representative Mongo explain
plans before making performance assumptions. Sorting candidate pages is bounded
in application memory and may still require examining all matching candidates.

`kedro gql mongo-indexes --apply` explicitly provisions configured indexes.
`kedro gql dataset-search check` reports consistent, missing, unsupported,
inconsistent, and failed projections. `kedro gql dataset-search rebuild`
recomputes projections without modifying source catalogs or tags. Each write
compares both source fields, including their presence, and retries up to three
times after concurrent changes. No maintenance runs at startup. Direct Mongo
writers bypass the builder; check/rebuild detects and repairs their stale data.
No new collection or mandatory migration is required. Deploy API and workers
together; index application, record rebuilds, and restarts are separate operations.

## Generic submission eligibility and worker extensions

`pipeline_submission_name_allowlist` restricts `pipelineSubmissionTemplates` and
all generic form, suggestion, upload, validation, and submission operations.
Unset means every generally visible pipeline is eligible; an empty list allows
none. General pipeline allow/disallow rules still apply. This list does not
restrict raw pipeline mutations or history search, allowing service webhooks to
run pipelines that are not offered by the generic form. The template query
filters before pagination and accepts limits from 1 through 200.

`celery_task_imports` adds application task modules to the worker's core imports.
For example, use `[molbio.cloning_submission]` to register custom shared tasks
without depending on API factory imports.

Selected local Kedro hooks receive `run_params["emit_pipeline_tags"]`, a callback
accepting a list of `{key: str, value: str}` pairs. The worker merges distinct
pairs into the owning current run through the backend's conditional document
update; unrelated tags remain intact and search projections are rebuilt by the
normal document builder. Events permit at most 1,000 tags, keys up to 256
characters, and values up to 4,096 characters. The callback exists only in child
runtime hook parameters and is not persisted in attempt records or transmitted
to external runners.


## Full archived log downloads and pipeline-name filtering

Monitoring opens by default in the shared UI. `pipelineLogDownload(id:)` returns a short-lived signed URL for the complete latest-attempt `events.jsonl` archive after SUCCESS, FAILURE, ABORTED, or REVOKED. It requires both `read_pipeline` and `subscribe_to_logs`, derives the path from the configured log root and recorded attempt, and does not read the archive into API memory. S3 downloads specify attachment disposition; local archives use the existing signed-file download route. Missing archives produce an actionable error. The bounded monitor preview remains separate from the complete download.
