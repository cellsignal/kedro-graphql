import jwt
import uuid
from .base import PreSignedUrlProvider
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path
from ...config import config as CONFIG
from fastapi import Request


class LocalFileProvider(PreSignedUrlProvider):
    """
    Implementation of PreSignedUrlProvider for a local file system.
    """

    def pre_signed_url_read(filepath: str, expires_in_sec: int) -> str | None:
        """
        Get a presigned URL for reading a dataset.

        Returns:
            str: A presigned URL for reading the dataset.
        """

        path = Path(filepath).resolve()

        payload = {
            "filepath": str(path),
            "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp()),
            "iat": int(datetime.now().timestamp())
        }

        token = jwt.encode(payload, CONFIG["KEDRO_GRAPHQL_JWT_SECRET_KEY"],
                           algorithm=CONFIG["KEDRO_GRAPHQL_JWT_ALGORITHM"])

        query = urlencode({"token": token})

        return f"{CONFIG['KEDRO_GRAPHQL_SERVER_URL']}/download?{query}"

    def pre_signed_url_create(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Get a presigned URL for creating a dataset.

        Returns:
            dict: A presigned URL for creating the dataset.
        """

        path = Path(filepath).resolve()

        # New unique path
        path, file = str(path).rsplit("/", 1)
        new_path = path + "/" + str(uuid.uuid4()) + "/" + file

        token = jwt.encode({
            "filepath": new_path,
            "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp())
        }, CONFIG["KEDRO_GRAPHQL_JWT_SECRET_KEY"], algorithm=CONFIG["KEDRO_GRAPHQL_JWT_ALGORITHM"])

        return {"url": f"{CONFIG['KEDRO_GRAPHQL_SERVER_URL']}/upload", "fields": {"token": token}}
