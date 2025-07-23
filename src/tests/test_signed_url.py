import pytest

import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import jwt
from .utilities import kedro_graphql_config
from kedro_graphql.signed_url.local_file_provider import LocalFileProvider
from kedro_graphql.models import DataSet


class TestLocalFileProvider:

    config = kedro_graphql_config()

    @pytest.fixture
    def mock_dataset(self, mock_text_in):
        return DataSet(name="test_dataset", config=json.dumps(
            {"type": "text.TextDataset", "filepath": str(mock_text_in)}))

    def test_create_allowed_local(self, mock_info_context, mock_dataset):
        output = LocalFileProvider.create(
            mock_info_context, mock_dataset, expires_in_sec=10)
        token = output["fields"].get("token", None)

        payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                             algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

        assert isinstance(payload, dict)

    def test_signed_url_read_allowed_local(self, mock_info_context, mock_dataset):
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
