import json
from .base import PreSignedUrlProvider
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path
from urllib.parse import quote


class LocalFileProvider(PreSignedUrlProvider):
    """
    Implementation of PreSignedUrlProvider for a local file system.
    """

    def pre_signed_url_read(config: dict) -> str | None:
        """
        Get a presigned URL for reading a dataset.

        Returns:
            str: A presigned URL for reading the dataset.
        """
        dataset_dict = json.loads(config)
        filepath = dataset_dict.get("filepath")

        path = Path(filepath).resolve()

        if not path.exists() or not path.is_file():
            return None

        token = str(uuid4())
        expiration = int((datetime.now() + timedelta(seconds=10)).timestamp())
        from ...commands import a as app
        app.presigned_urls[token] = (filepath, expiration)
        return f"/download/{quote(filepath)}?token={token}&Expires={expiration}"

    def pre_signed_url_create(self) -> dict | None:
        """
        Get a presigned URL for creating a dataset.

        Returns:
            dict: A presigned URL for creating the dataset.
        """
        pass
