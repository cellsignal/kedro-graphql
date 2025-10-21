import pytest

import json
from ..utilities import kedro_graphql_config
from kedro_graphql.signed_url.s3_provider import S3Provider
from kedro_graphql.models import DataSet


class TestS3Provider:
    config = kedro_graphql_config()

    @pytest.fixture
    def mock_s3_client(self, mocker):
        """Fixture to mock boto3 S3 client"""
        mock_boto3 = mocker.patch("kedro_graphql.signed_url.s3_provider.boto3")
        mock_s3 = mock_boto3.client.return_value
        mock_s3.generate_presigned_url.return_value = "https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time"
        mock_s3.generate_presigned_post.return_value = {
            "url": "https://your-bucket-name.s3.amazonaws.com/",
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

    def test_read(self, mock_s3_client, mock_info_context, mock_dataset):
        """Test reading a single file from a TextDataset"""

        output = S3Provider.read(
            mock_info_context, mock_dataset, expires_in_sec=10)

        assert isinstance(output, str)

        assert output == "https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time"

    def test_read_partitions(self, mock_s3_client, mock_info_context, mock_partitioned_dataset):
        """Test reading multiple partitions from a PartitionedDataset"""

        output = S3Provider.read(
            mock_info_context, mock_partitioned_dataset, expires_in_sec=10, partitions=["part-0001", "part-0002"])
        assert isinstance(output, list)
        for url in output:
            assert url == "https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time"

    def test_create(self, mock_s3_client, mock_info_context, mock_dataset):
        """Test creating a single signed URL for uploading a TextDataset"""

        output = S3Provider.create(
            mock_info_context, mock_dataset, expires_in_sec=10)

        assert isinstance(output, dict)

        assert output == {
            "url": "https://your-bucket-name.s3.amazonaws.com/",
            "fields": {
                "key": "your-object-key",
                "AWSAccessKeyId": "YOUR_ACCESS_KEY_ID",
                "policy": "YOUR_BASE64_ENCODED_POLICY",
                "signature": "YOUR_SIGNATURE",
                "Content-Type": "application/octet-stream"
            }
        }

    def test_create_partitions(self, mock_s3_client, mock_info_context, mock_partitioned_dataset):
        """Test creating signed URLs for the upload of specific partitions in a PartitionedDataset"""

        output = S3Provider.create(
            mock_info_context, mock_partitioned_dataset, expires_in_sec=10, partitions=["part-0001", "part-0002"])
        assert isinstance(output, list)

        for item in output:
            assert item == {
                "url": "https://your-bucket-name.s3.amazonaws.com/",
                "fields": {
                    "key": "your-object-key",
                    "AWSAccessKeyId": "YOUR_ACCESS_KEY_ID",
                    "policy": "YOUR_BASE64_ENCODED_POLICY",
                    "signature": "YOUR_SIGNATURE",
                    "Content-Type": "application/octet-stream"
                }
            }
