## PreSignedUrlProvider

The `kedro_graphql.presigned_url` module provides a standardized interface for generating presigned URLs for reading and writing datasets. This enables secure, time-limited access to files for upload and download operations, commonly used for cloud storage and local file systems.

### Purpose

- Abstracts the logic for generating presigned URLs for different storage backends.
- Allows the Kedro GraphQL API to support secure file transfers without exposing credentials or direct access.
- Supports both reading (download) and creating (upload) operations.

### Available Providers

- **LocalFileProvider**
    - Generates presigned URLs for files stored on the local filesystem.
    - Uses JWT tokens to authorize access and provides endpoints for upload/download.

- **S3PreSignedUrlProvider**
    - Generates AWS S3 presigned URLs for objects in S3 buckets.
    - Uses AWS credentials and boto3 to create time-limited URLs for both upload (POST) and download (GET).

### How to Use

The provider is selected via configuration (e.g., in your config or YAML spec):

```yaml
config:
  KEDRO_GRAPHQL_PRESIGNED_URL_PROVIDER: "kedro_graphql.presigned_url.s3_provider.S3PreSignedUrlProvider"
```

Or for local files:

```yaml
config:
  KEDRO_GRAPHQL_PRESIGNED_URL_PROVIDER: "kedro_graphql.presigned_url.local_file_provider.LocalFileProvider"
```

The API will use the configured provider to generate presigned URLs for dataset operations.

### Additional Configuration Attributes

You can further customize the behavior of presigned URL providers using the following configuration attributes:

#### Common
- `KEDRO_GRAPHQL_PRESIGNED_URL_MAX_EXPIRES_IN_SEC`: Maximum allowed expiration time (in seconds) for any presigned URL. Default is `43200` (12 hours).

#### LocalFileProvider
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL`: The base URL for the local file server (e.g., `http://localhost:5000`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY`: Secret key used to sign JWT tokens for file access.
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM`: Algorithm used for JWT signing (e.g., `HS256`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS`: List of allowed root directories for downloads (e.g., `["./data", "/var"]`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS`: List of allowed root directories for uploads (e.g., `["./data"]`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB`: Maximum allowed upload file size in megabytes (default: `10`).

#### S3PreSignedUrlProvider
- Uses standard AWS credentials and configuration via `boto3` (see [boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)).
- No additional custom attributes are required; ensure your environment is configured for AWS access.

These attributes can be set in your YAML config or environment to control security, access, and operational limits for presigned URL operations.

