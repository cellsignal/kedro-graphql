## Secure Dataset Uploads & Downloads with Signed URLs

Kedro-graphql enables secure, time-limited access to datasets for both upload and download operations using signed URLs. This approach allows clients to request a signed URL from the GraphQL API, which can then be used to interact directly with the storage backend (local file server or S3).

**Typical workflow:**

1. Client requests a signed URL for upload or download via a GraphQL mutation or query.
2. The API generates a signed URL and returns it to the client.
3. The client uses the signed URL to upload or download the dataset directly from the storage backend.

### Example Flow

```mermaid
flowchart TD
    client[Client]
    api[GraphQL API]
    provider[SignedUrlProvider]
    storage[Storage Backend: Local File Server or S3]

    client -->|'1. Request signed URL'| api
    api -->|'2. Request signed URL'| provider
    provider -->|'3. Generate signed URL'| api
    api --> | '4. Return signed URL' | client
    client -->|'5. Upload/Download dataset using signed URL'| storage
```
## SignedUrlProvider

The `kedro_graphql.signed_url` module provides a standardized interface for generating signed URLs for reading and writing datasets. This enables secure, time-limited access to files for upload and download operations, commonly used for cloud storage and local file systems.

### Purpose

- Abstracts the logic for generating signed URLs for different storage backends.
- Allows the Kedro GraphQL API to support secure file transfers without exposing credentials or direct access.
- Supports both reading (download) and creating (upload) operations.



### Available Providers

- **LocalFileProvider**
    - Generates signed URLs for files stored on the local filesystem.
    - Uses JWT tokens to authorize access and uses the following REST endpoints:
        - `/upload`
        - `/download`


- **S3Provider**
    - Generates AWS S3 presigned URLs for objects in S3 buckets.
    - Uses AWS credentials and boto3 to create time-limited URLs for both upload (POST) and download (GET).

### How to Use

The provider is selected via configuration (e.g., in your config or YAML spec):

```yaml
config:
  KEDRO_GRAPHQL_SIGNED_URL_PROVIDER: "kedro_graphql.signed_url.s3_provider.S3Provider"
```

Or for local files:

```yaml
config:
  KEDRO_GRAPHQL_SIGNED_URL_PROVIDER: "kedro_graphql.signed_url.local_file_provider.LocalFileProvider"
```

The API will use the configured provider to generate signed URLs for dataset operations.

### GraphQL Examples: `readDatasets` and `createDatasets`

Both `readDatasets` (query) and `createDatasets` (mutation) return one signed-url object per dataset input. For non-partitioned datasets you get a `SignedUrl`. For partitioned datasets you get a `SignedUrls` wrapper containing an array.

#### `readDatasets` query

```graphql
query ReadDatasets($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
  readDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec) {
    __typename
    ... on SignedUrl {
      url
      file
      fields {
        name
        value
      }
    }
    ... on SignedUrls {
      urls {
        url
        file
        fields {
          name
          value
        }
      }
    }
    ... on DataSet {
      name
      partitions
    }
  }
}
```

Example variables (single dataset):

```json
{
  "id": "PIPELINE_ID",
  "datasets": [{ "name": "text_in" }],
  "expires_in_sec": 3600
}
```

Example response shape (local-file provider):

```json
{
  "data": {
    "readDatasets": [
      {
        "__typename": "SignedUrl",
        "url": "http://localhost:5000/download?token=...",
        "file": "text_in.txt",
        "fields": [{ "name": "token", "value": "JWT_TOKEN" }]
      }
    ]
  }
}
```

Partitioned datasets use a two-step flow:

1. Discover available partition keys.
2. Request signed URLs for the partition keys you want to read.

Step 1: discover partition keys

```json
{
  "id": "PIPELINE_ID",
  "datasets": [
    {
      "name": "my_partitioned_dataset",
      "list_partitions": true
    }
  ],
  "expires_in_sec": 3600
}
```

Expected response shape for partition discovery:

```json
{
  "data": {
    "readDatasets": [
      {
        "__typename": "DataSet",
        "name": "my_partitioned_dataset",
        "partitions": [
          "2026-05-01",
          "2026-05-02"
        ]
      }
    ]
  }
}
```

Step 2: request signed URLs for selected partitions

```json
{
  "id": "PIPELINE_ID",
  "datasets": [
    {
      "name": "my_partitioned_dataset",
      "partitions": ["part-1", "part-2"]
    }
  ],
  "expires_in_sec": 3600
}
```

!!! Note

    Do not combine `listPartitions` and `partitions` in the same dataset input. If both are provided, `listPartitions` takes precedence and returns partition metadata (`DataSet`) instead of signed URLs.


#### `createDatasets` mutation

```graphql
mutation CreateDatasets(
  $id: String!
  $datasets: [DataSetInput!]!
  $expires_in_sec: Int!
) {
  createDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec) {
    __typename
    ... on SignedUrl {
      url
      file
      fields {
        name
        value
      }
    }
    ... on SignedUrls {
      urls {
        url
        file
        fields {
          name
          value
        }
      }
    }
  }
}
```

Example variables (create/upload signed URLs for datasets):

```json
{
  "id": "PIPELINE_ID",
  "datasets": [{ "name": "text_out" }],
  "expires_in_sec": 3600
}
```

Example response shape (local-file provider):

```json
{
  "data": {
    "createDatasets": [
      {
        "__typename": "SignedUrl",
        "url": "http://localhost:5000/upload",
        "file": "text_out.txt",
        "fields": [{ "name": "token", "value": "JWT_TOKEN" }]
      }
    ]
  }
}
```
Use `SignedUrl.url` as the upload endpoint and submit `SignedUrl.fields` as the required form fields (along with the file payload).

If the underlying dataset type is a `partitions.PartitionedDataset`, `createDatasets` requires `partitions` to be provided inside each `DataSetInput`.

### Additional Configuration

You can further customize the behavior of signed URL providers using the following configuration attributes:

#### Common
- `KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC`: Maximum allowed expiration time (in seconds) for any signed URL. Default is `43200` (12 hours).

#### LocalFileProvider
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL`: The base URL for the local file server (e.g., `http://localhost:5000`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY`: Secret key used to sign JWT tokens for file access.
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM`: Algorithm used for JWT signing (e.g., `HS256`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS`: List of allowed root directories for downloads (e.g., `["./data", "/var"]`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS`: List of allowed root directories for uploads (e.g., `["./data"]`).
- `KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB`: Maximum allowed upload file size in megabytes (default: `10`).

#### S3Provider
- Uses standard AWS credentials and configuration via `boto3` (see [boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)).
- No additional custom attributes are required; ensure your environment is configured for AWS access.


### Implementing a Custom SignedUrlProvider

To implement your own provider, create a new class that inherits from the `SignedUrlProvider` abstract base class and implement the required methods:

```python
from kedro_graphql.signed_url.base import SignedUrlProvider

class MyCustomProvider(SignedUrlProvider):

    def read(info: Info, dataset: DataSet, expires_in_sec: int) -> str | None:
        """
        Method to get a signed URL for downloading a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset for which to create a signed URL.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            str | None: A signed URL for downloading the dataset.
        """
        # Your logic to generate a signed URL for reading
        pass

    def create(info: Info, dataset: DataSet, expires_in_sec: int) -> dict | None:
        """
        Method to get a signed URL for uploading a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset for which to create a signed URL.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            dict | None: A dictionary with the URL to post to and form fields and values to submit with the POST.
        """
        # Your logic to generate a signed URL for uploading
        pass

```

- `read`: Should return a signed URL for downloading the dataset.
- `create`: Should return a dictionary with the upload URL and any required form fields for uploading the dataset.

Once implemented, set your provider in the configuration:

```yaml
config:
  KEDRO_GRAPHQL_SIGNED_URL_PROVIDER: "path.to.MyCustomProvider"
```

This allows the API to use your custom logic for generating signed URLs for dataset operations.

