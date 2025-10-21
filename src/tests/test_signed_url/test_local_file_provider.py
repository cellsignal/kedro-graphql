import pytest

import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import jwt
from ..utilities import kedro_graphql_config
from kedro_graphql.signed_url.local_file_provider import LocalFileProvider
from kedro_graphql.models import DataSet


class TestLocalFileProvider:

    config = kedro_graphql_config()

    @pytest.fixture
    def mock_dataset(self, mock_text_in):
        """Fixture for a TextDataset pointing to a test data file"""

        return DataSet(name="test_dataset", config=json.dumps(
            {"type": "text.TextDataset", "filepath": str(mock_text_in)}))

    @pytest.fixture
    def mock_partitioned_dataset(self):
        """Fixture for a PartitionedDataset pointing to test data files"""
        return DataSet(name="test_partitioned_dataset", config=json.dumps(
            {"type": "partitions.PartitionedDataset",
             "path": str(Path("src/tests/data/partitioned_dataset/").resolve()),
             "filename_suffix": ".txt",
             "dataset": {"type": "text.TextDataset"}}
        ))

    def test_create_allowed_local(self, mock_info_context, mock_dataset):
        """Test creating a signed URL for a TextDataset"""

        output = LocalFileProvider.create(
            mock_info_context, mock_dataset, expires_in_sec=10)
        token = output["fields"].get("token", None)

        payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                             algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

        assert isinstance(payload, dict)

    def test_create_partitioned_local(self, mock_info_context, mock_partitioned_dataset):
        """Test creating signed URLs for specific partitions from a PartitionedDataset"""

        partitions = ["part-0001", "part-0002"]
        output = LocalFileProvider.create(
            mock_info_context, mock_partitioned_dataset, expires_in_sec=10, partitions=partitions)
        assert isinstance(output, list)

        expected_files = [mock_partitioned_dataset.parse_config()["path"] + "/" + f + ".txt" for f in
                          partitions]

        for item in output:
            assert item.keys() == {"url", "fields"}
            assert "token" in item["fields"]
            token = item["fields"].get("token", None)

            payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                                 algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

            assert isinstance(payload, dict)
            assert "filepath" in payload
            assert "exp" in payload
            assert "iat" in payload
            assert payload["filepath"] in expected_files

    def test_signed_url_read_allowed_local(self, mock_info_context, mock_dataset):
        """Test reading a single file from a TextDataset"""

        output = LocalFileProvider.read(
            mock_info_context, mock_dataset, expires_in_sec=10)
        parsed_url = urlparse(output)
        query_params = parse_qs(parsed_url.query)
        token = query_params.get("token", [None])[0]

        payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                             algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

        assert isinstance(payload, dict)

        c = json.loads(mock_dataset.config)
        assert Path(payload["filepath"]).resolve() == Path(c["filepath"]).resolve()

    def test_read_partitioned_local_00(self, mock_info_context, mock_partitioned_dataset):
        """Test reading all partitions from a PartitionedDataset"""

        output = LocalFileProvider.read(
            mock_info_context, mock_partitioned_dataset, expires_in_sec=10)
        assert isinstance(output, list)

        expected_files = [mock_partitioned_dataset.parse_config()["path"] + "/" + f for f in
                          ["part-0001.txt", "part-0002.txt"]]

        for url in output:
            token = urlparse(url).query.split("token=")[1]

            payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                                 algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

            assert isinstance(payload, dict)
            assert "filepath" in payload
            assert "exp" in payload
            assert "iat" in payload
            assert payload["filepath"] in expected_files

    def test_read_partitioned_local_01(self, mock_info_context, mock_partitioned_dataset):
        """Test reading specific partitions from a PartitionedDataset"""

        output = LocalFileProvider.read(
            mock_info_context, mock_partitioned_dataset, expires_in_sec=10, partitions=["part-0001"])

        assert isinstance(output, list)

        expected_files = [mock_partitioned_dataset.parse_config()["path"] + "/" + f for f in
                          ["part-0001.txt"]]

        for url in output:
            token = urlparse(url).query.split("token=")[1]

            payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                                 algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

            assert isinstance(payload, dict)
            assert "filepath" in payload
            assert "exp" in payload
            assert "iat" in payload
            assert payload["filepath"] in expected_files
