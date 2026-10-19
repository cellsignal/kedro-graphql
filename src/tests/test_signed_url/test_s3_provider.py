import pytest

import json
from ..utilities import kedro_graphql_config
from kedro_graphql.signed_url.s3_provider import S3Provider
from kedro_graphql.models import DataSet, SignedUrl, SignedUrls


class TestS3Provider:
    config = kedro_graphql_config()

    @pytest.fixture
    def mock_s3_client(self, mocker):
        """Fixture to mock boto3 S3 client"""
        mock_boto3 = mocker.patch("kedro_graphql.signed_url.s3_provider.boto3")
        mock_s3 = mock_boto3.client.return_value
        mock_s3.head_object.return_value = {"ContentLength": 123}
        mock_s3.generate_presigned_url.return_value = "https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time"
        mock_s3.generate_presigned_post.return_value = {
            "url": "https://your-bucket-name.s3.amazonaws.com/",
            "file": "your-object-key",
            "fields": {
                "key": "your-object-key",
                "AWSAccessKeyId": "YOUR_ACCESS_KEY_ID",
                "policy": "YOUR_BASE64_ENCODED_POLICY",
                "signature": "YOUR_SIGNATURE",
                "Content-Type": "application/octet-stream"
            }
        }
        return mock_s3

    @pytest.fixture
    def mock_dataset(self):
        """Fixture for a TextDataset pointing to a test data file"""

        return DataSet(name="test_dataset", config=json.dumps(
            {"type": "text.TextDataset", "filepath": "s3://my-bucket/path/to/file.txt"}))

    @pytest.fixture
    def mock_partitioned_dataset(self):
        """Fixture for a PartitionedDataset pointing to test partitions"""
        return DataSet(name="test_partitioned_dataset", config=json.dumps(
            {"type": "partitions.PartitionedDataset",
             "path": "s3://my-bucket/path/to/partitioned_dataset",
             "filename_suffix": ".txt",
             "dataset": {"type": "text.TextDataset"}}
        ))

    def test_read(self, mock_s3_client, mock_info, mock_dataset):
        """Test reading a single file from a TextDataset"""

        output = S3Provider.read(
            mock_info, mock_dataset, expires_in_sec=10)

        assert isinstance(output, SignedUrl)

        assert output.url == "https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time"
        assert output.size == 123

    def test_read_partitions(self, mock_s3_client, mock_info, mock_partitioned_dataset):
        """Test reading multiple partitions from a PartitionedDataset"""

        output = S3Provider.read(
            mock_info, mock_partitioned_dataset, expires_in_sec=10, partitions=["part-0001", "part-0002"])
        assert isinstance(output, SignedUrls)
        for url in output.urls:
            assert url.url == "https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time"

    def test_create(self, mock_s3_client, mock_info, mock_dataset):
        """Test creating a single signed URL for uploading a TextDataset"""

        output = S3Provider.create(
            mock_info, mock_dataset, expires_in_sec=10)

        assert isinstance(output, SignedUrl)

        assert output == SignedUrl.from_graphql({
            "url": "https://your-bucket-name.s3.amazonaws.com/",
            "file": "file.txt",
            "fields": [
                {"name": "key", "value": "your-object-key"},
                {"name": "AWSAccessKeyId", "value": "YOUR_ACCESS_KEY_ID"},
                {"name": "policy", "value": "YOUR_BASE64_ENCODED_POLICY"},
                {"name": "signature", "value": "YOUR_SIGNATURE"},
                {"name": "Content-Type", "value": "application/octet-stream"}
            ]
        })

    def test_create_partitions(self, mock_s3_client, mock_info, mock_partitioned_dataset):
        """Test creating signed URLs for the upload of specific partitions in a PartitionedDataset"""

        output = S3Provider.create(
            mock_info, mock_partitioned_dataset, expires_in_sec=10, partitions=["part-0001", "part-0002"])
        assert isinstance(output, SignedUrls)

        expected = SignedUrls(urls=[
            SignedUrl.from_graphql({
                "url": "https://your-bucket-name.s3.amazonaws.com/",
                "file": "part-0001.txt",
                "fields": [
                    {"name": "key", "value": "your-object-key"},
                    {"name": "AWSAccessKeyId", "value": "YOUR_ACCESS_KEY_ID"},
                    {"name": "policy", "value": "YOUR_BASE64_ENCODED_POLICY"},
                    {"name": "signature", "value": "YOUR_SIGNATURE"},
                    {"name": "Content-Type", "value": "application/octet-stream"}
                ]
            }),
            SignedUrl.from_graphql({
                "url": "https://your-bucket-name.s3.amazonaws.com/",
                "file": "part-0002.txt",
                "fields": [
                    {"name": "key", "value": "your-object-key"},
                    {"name": "AWSAccessKeyId", "value": "YOUR_ACCESS_KEY_ID"},
                    {"name": "policy", "value": "YOUR_BASE64_ENCODED_POLICY"},
                    {"name": "signature", "value": "YOUR_SIGNATURE"},
                    {"name": "Content-Type", "value": "application/octet-stream"}
                ]
            })
        ])

        for index, item in enumerate(output.urls):
            assert item == expected.urls[index]


@pytest.mark.parametrize("trailing_slash", ["", "/"])
@pytest.mark.parametrize("method", ["read", "create"])
@pytest.mark.parametrize("explicit", [True, False])
def test_partition_keys_have_one_separator(trailing_slash, method, explicit, mocker, mock_info):
    client = mocker.patch("kedro_graphql.signed_url.s3_provider.boto3.client").return_value
    client.head_object.return_value = {"ContentLength": 123}
    client.generate_presigned_url.return_value = "https://example.invalid/file"
    client.generate_presigned_post.return_value = {"url": "https://example.invalid", "fields": {}}
    mocker.patch("kedro_graphql.signed_url.s3_provider.AbstractDataset.from_config").return_value.load.return_value = {"nested/part": None}
    dataset = DataSet(name="parts", config=json.dumps({"type": "partitions.PartitionedDataset", "path": "s3://bucket/root" + trailing_slash, "filename_suffix": ".txt", "dataset": {"type": "text.TextDataset"}}))
    result = getattr(S3Provider, method)(mock_info, dataset, 10, ["nested/part"] if explicit else None)
    assert len(result.urls) == 1
    if method == "read":
        client.head_object.assert_called_once_with(Bucket="bucket", Key="root/nested/part.txt")
    else:
        assert client.generate_presigned_post.call_args.args[1] == "root/nested/part.txt"


def test_missing_partition_has_actionable_error(mocker, mock_info):
    from kedro_graphql.exceptions import DataSetError
    mocker.patch.object(S3Provider, "presigned_url", return_value=None)
    dataset = DataSet(name="parts", config=json.dumps({"type": "partitions.PartitionedDataset", "path": "s3://bucket/root/", "filename_suffix": ".txt", "dataset": {"type": "text.TextDataset"}}))
    with pytest.raises(DataSetError, match="Cannot sign partition.*missing.txt"):
        S3Provider.read(mock_info, dataset, 10, ["missing"])
