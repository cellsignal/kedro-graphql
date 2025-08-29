The following table describes each configuration attribute available:

| Attribute                              | Type | Default | Description                                                                                      |
|-----------------------------------------|------|---------|--------------------------------------------------------------------------------------------------|
| `app`                                  | string | `kedro_graphql.asgi.KedroGraphQL` | Python path to the ASGI application callable.                                                    |
| `app_description`                      | string | `A tool for serving kedro projects as a GraphQL API` | Description of the Kedro GraphQL application.                                                    |
| `app_title`                            | string | `Kedro GraphQL API` | Title of the Kedro GraphQL application.                                                          |
| `backend`                              | string | `kedro_graphql.backends.mongodb.MongoBackend` | Python path to the backend class for data storage and retrieval.                                 |
| `broker`                               | string | `redis://localhost` | URI for the message broker (e.g., Redis) used for task queueing.                                |
| `celery_result_backend`                 | string | `redis://localhost` | URI for the Celery result backend (e.g., Redis).                                                 |
| `conf_source`                          | string | `None` | Optional path to an alternative configuration source.                                             |
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
| `log_path_prefix`                      | string | `None` | Optional prefix for log file paths.                                                              |
| `log_tmp_dir`                          | string | auto-generated | Directory path for temporary log files.                                                          |
| `mongo_db_collection`                   | string | `pipelines` | Name of the MongoDB collection to use.                                                           |
| `mongo_db_name`                        | string | `pipelines` | Name of the MongoDB database to use.                                                             |
| `mongo_uri`                            | string | `mongodb://root:example@localhost:27017/` | MongoDB connection URI string.                                                                   |
| `permissions`                          | string | `kedro_graphql.permissions.IsAuthenticatedAlways` | Python path to the permissions class used for authentication.                                    |
| `permissions_group_to_role_map`        | dict | `{"EXTERNAL_GROUP_NAME": "admin"}` | Mapping of external group names to roles. Specify as JSON string when using CLI/environment variables. |
| `permissions_role_to_action_map`       | dict | `{"admin": [...]}` | Mapping of roles to allowed actions. Specify as JSON string when using CLI/environment variables. |
| `project_version`                      | string | `None` | Version of the Kedro GraphQL project.                                                            |
| `root_path`                            | string | `""` | Root path for all API endpoints (e.g., '/api/v1'). When set, all API routes will be prefixed with this path. |
| `runner`                               | string | `kedro.runner.SequentialRunner` | Python path to the Kedro runner class.                                                           |
| `signed_url_max_expires_in_sec`    | integer | `43200` | Maximum allowed expiration time (in seconds) for presigned URLs. Default: 12 hours. |
| `signed_url_provider`                  | string | `kedro_graphql.signed_url.s3_provider.S3Provider` | Python path to the presigned URL provider class (e.g., for S3 or local file support). |



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
  app: "kedro_graphql.asgi.KedroGraphQL"
  app_description: "A tool for serving kedro projects as a GraphQL API"
  app_title: "Kedro GraphQL"
  backend: "kedro_graphql.backends.mongodb.MongoBackend"
  broker: "redis://localhost"
  celery_result_backend: "redis://localhost"
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
| app                                                | --app                                            | kedro_graphql.asgi.KedroGraphQL                      |
| app_title                                          | --app-title                                      | "My Custom Kedro GraphQL"                           |
| app_description                                    | --app-description                                | "Custom description"                                 |
| backend                                            | --backend                                        | kedro_graphql.backends.mongodb.MongoBackend         |
| broker                                             | --broker                                         | redis://localhost                                    |
| celery_result_backend                              | --celery-result-backend                          | redis://localhost                                    |
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
