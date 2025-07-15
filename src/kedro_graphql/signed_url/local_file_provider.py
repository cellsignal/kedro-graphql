import jwt
import uuid
from .base import SignedUrlProvider
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path
from ..config import load_config

CONFIG = load_config()


class LocalFileProvider(SignedUrlProvider):
    """
    Implementation of SignedUrlProvider for a local file system.
    """

    def read(filepath: str, expires_in_sec: int) -> str | None:
        """
        Get a signed URL for reading a dataset.

        Returns:
            str: A signed URL for reading the dataset.
        """

        path = Path(filepath).resolve()

        payload = {
            "filepath": str(path),
            "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp()),
            "iat": int(datetime.now().timestamp())
        }

        token = jwt.encode(payload, CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                           algorithm=CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"])

        query = urlencode({"token": token})

        return f"{CONFIG['KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL']}/download?{query}"

    def create(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Get a signed URL for creating a dataset.

        Returns:
            dict: A signed URL for creating the dataset.
        """

        path = Path(filepath).resolve()

        # New unique path
        path, file = str(path).rsplit("/", 1)
        new_path = path + "/" + str(uuid.uuid4()) + "/" + file

        token = jwt.encode(
            {"filepath": new_path, "exp": int(
                (datetime.now() + timedelta(seconds=expires_in_sec)).timestamp())},
            CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
            algorithm=CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"])

        return {"url": f"{CONFIG['KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL']}/upload", "fields": {"token": token}}
