import pytest

from pathlib import Path
from urllib.parse import urlparse, parse_qs
import jwt
from .utilities import kedro_graphql_config
from kedro_graphql.signed_url.local_file_provider import LocalFileProvider


class TestLocalFileProvider:

    config = kedro_graphql_config()

    def test_create_allowed_local(self, mock_text_in):

        output = LocalFileProvider.create(filepath=str(mock_text_in), expires_in_sec=10)
        token = output["fields"].get("token", None)

        payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                             algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

        # Unique path should be generated
        assert Path(payload["filepath"]).resolve() != Path(mock_text_in).resolve()

    def test_signed_url_read_allowed_local(self, mock_text_in):
        output = LocalFileProvider.read(filepath=str(mock_text_in), expires_in_sec=10)
        parsed_url = urlparse(output)
        query_params = parse_qs(parsed_url.query)
        token = query_params.get("token", [None])[0]

        payload = jwt.decode(token, self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                             algorithms=[self.config["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"]])

        assert Path(payload["filepath"]).resolve() == Path(mock_text_in).resolve()
