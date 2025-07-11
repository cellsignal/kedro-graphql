The following table describes each configuration attribute available:

| Attribute                              | Description                                                                                      |
|-----------------------------------------|--------------------------------------------------------------------------------------------------|
| `mongo_uri`                            | MongoDB connection URI string.                                                                   |
| `mongo_db_name`                        | Name of the MongoDB database to use.                                                             |
| `mongo_db_collection`                   | Name of the MongoDB collection to use.                                                           |
| `imports`                              | List of Python modules to import for plugin registration.                                        |
| `app`                                  | Python path to the ASGI application callable.                                                    |
| `app_title`                            | Title of the Kedro GraphQL application.                                                          |
| `app_description`                      | Description of the Kedro GraphQL application.                                                    |
| `project_version`                      | Version of the Kedro GraphQL project.                                                            |
| `backend`                              | Python path to the backend class for data storage and retrieval.                                 |
| `broker`                               | URI for the message broker (e.g., Redis) used for task queueing.                                |
| `celery_result_backend`                 | URI for the Celery result backend (e.g., Redis).                                                 |
| `runner`                               | Python path to the Kedro runner class.                                                           |
| `env`                                  | Environment name (e.g., "local").                                                                |
| `conf_source`                          | Optional path to an alternative configuration source.                                             |
| `deprecation_docs`                     | URL to documentation about deprecated features.                                                  |
| `log_tmp_dir`                          | Directory path for temporary log files.                                                          |
| `log_path_prefix`                      | Optional prefix for log file paths.                                                              |
| `events_config`                        | Dictionary mapping event names to their configuration (source, type, etc.).                      |
| `permissions`                          | Python path to the permissions class used for authentication.                                    |
| `permissions_role_to_action_mapping`   | Mapping of roles to allowed actions within the API.                                              |
| `permissions_group_to_role_mapping`    | Mapping of external group names to roles for access control.                                     |
| `presigned_url_max_expires_in_sec`    | Maximum allowed expiration time (in seconds) for presigned URLs. Default: `43200` (12 hours). |
| `local_file_provider_server_url`       | Base URL for the local file server (e.g., `http://localhost:5000`).                             |
| `local_file_provider_jwt_secret_key`   | Secret key for signing JWT tokens for local file access.                                        |
| `local_file_provider_jwt_algorithm`    | Algorithm used for JWT signing (e.g., `HS256`).                                                |
| `local_file_provider_download_allowed_roots` | List of allowed root directories for downloads.                                          |
| `local_file_provider_upload_allowed_roots`   | List of allowed root directories for uploads.                                            |
| `local_file_provider_upload_max_file_size_mb` | Maximum allowed upload file size in megabytes. Default: `10`.                            |
| `events_config`                        | Dictionary for event configuration.                                                              |
| `permissions`                          | Python path to the permissions class used for authentication.                                    |
| `permissions_role_to_action_map`       | Mapping of roles to allowed actions.                                                              |
| `permissions_group_to_role_map`        | Mapping of external group names to roles.                                                        |
| `presigned_url_provider`                  | Python path to the presigned URL provider class (e.g., for S3 or local file support). |



Configuration can be supplied through one or more of the following methods:

- [environment](#environment)
- ```.env``` file
- [command line](#commandline)
- [YAML API Spec](##yamlapispec)


## Environment

When using environment varialbes the configration attribute name should
be uppercase and prefixed with `KEDRO_GRAPHQL_`

```bash
## example .env file
KEDRO_GRAPHQL_MONGO_URI=mongodb://root:example@localhost:27017/
KEDRO_GRAPQHL_MONGO_DB_NAME=pipelines
KEDRO_GRAPHQL_IMPORTS=kedro_graphql.plugins.plugins
KEDRO_GRAPHQL_APP=kedro_graphql.asgi.KedroGraphQL
KEDRO_GRAPHQL_BACKEND=kedro_graphql.backends.mongodb.MongoBackend
KEDRO_GRAPHQL_BROKER=redis://localhost
KEDRO_GRAPHQL_CELERY_RESULT_BACKEND=redis://localhost
KEDRO_GRAPHQL_RUNNER=kedro.runner.SequentialRunner
KEDRO_GRAPHQL_ENV=local
KEDRO_GRAPHQL_CONF_SOURCE=None
KEDRO_GRAPHQL_LOG_TMP_DIR=my_tmp_dir/
KEDRO_GRAPHQL_LOG_PATH_PREFIX=s3://my-bucket/
KEDRO_GRAPHQL_PRESIGNED_URL_MAX_EXPIRES_IN_SEC=43200
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL=http://localhost:5000
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY=your_secret_key
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM=HS256
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS=/path/to/download
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS=/path/to/upload
KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB=10
```

## Command line

The configuration can also be provided at startup through the cli interface.
Configuration values can be mapped to the the appropriate cli option by
removing the "KEDRO_GRAPHQL_" prefix and using a lower case, hyphen format
for the remaining string.  For example:

| configuration attribute      | cli option           | example                                   |
|----------------------------|----------------------|-------------------------------------------|
| mongo_uri                  | --mongo-uri          | mongodb://root:example@localhost:27017/   |
| mongo_db_name              | --mongo-db-name      | pipelines                                 |
| imports                    | --imports            | kedro_graphql.plugins.plugins             |
| app                        | --app                | kedro_graphql.asgi.KedroGraphQL           |
| backend                    | --backend            | kedro_graphql.backends.mongodb.MongoBackend|
| broker                     | --broker             | redis://localhost                         |
| celery_result_backend      | --celery-result-backend| redis://localhost                       |
| runner                     | --runner             | kedro.runner.SequentialRunner             |
| env                        | --env                | local                                     |
| conf_source                | --conf-source        | $HOME/myproject/conf                      |
| log_tmp_dir                | --log-tmp-dir        | my_tmp_dir/                               |
| log_path_prefix            | --log-path-prefix    | s3://my-bucket/                           |


## YAML API Specification

The YAML API uses a snake case format without the `KEDRO_GRAPHQL_` prefix.

```yaml
## Kedro GraphQL YAML API configuration file.
config:
  mongo_uri: "mongodb://root:example@localhost:27017/"
  mongo_db_name: "pipelines"
  mongo_db_collection: "pipelines" 
  imports:
    - "kedro_graphql.plugins.plugins"
  app: "kedro_graphql.asgi.KedroGraphQL"
  app_title: "Kedro GraphQL"
  app_description: "A tool for serving kedro projects as a GraphQL API"
  project_version: "1.0.1"
  backend: "kedro_graphql.backends.mongodb.MongoBackend"
  broker: "redis://localhost"
  celery_result_backend: "redis://localhost"
  runner: kedro.runner.SequentialRunner"
  env: "local"
  conf_source: null
  deprecation_docs: "https://github.com/opensean/kedro-graphql/blob/main/README.md#deprecations"
  log_tmp_dir: "/tmp/"
  log_path_prefix: null
  events_config:
    event00:
      source: "example.com"
      type: "com.example.event"
  permissions: "kedro_graphql.permissions.IsAuthenticatedXForwardedEmail"
  permissions_role_to_action_mapping:
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
  permissions_group_to_role_mapping: 
      EXTERNAL_GROUP_NAME: 
          - admin


```


Use the `--api-spec` flag to specify the path to the configuration file 

```
kedro gql --api-spec api.yaml
```