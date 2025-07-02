import jwt
import uuid
from .base import PreSignedUrlProvider
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path
from ...config import config as CONFIG


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

        ALLOWED_ROOTS = []

        for root in CONFIG["KEDRO_GRAPHQL_PRESIGNED_URL_DOWNLOAD_ALLOWED_ROOTS"]:
            ALLOWED_ROOTS.append(Path(root).resolve())
            print(f"Allowed root: {Path(root).resolve()}")

        if not any(path.is_relative_to(root) for root in ALLOWED_ROOTS):
            raise ValueError(
                f"Path {path} is not allowed. Allowed roots: {ALLOWED_ROOTS}"
            )

        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist or is not a file.")

        if not path.is_file():
            raise ValueError(f"Path {path} is not a file.")

        payload = {
            "filepath": str(path),
            "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp()),
            "iat": int(datetime.now().timestamp())
        }

        token = jwt.encode(payload, CONFIG["KEDRO_GRAPHQL_JWT_SECRET_KEY"],
                           algorithm=CONFIG["KEDRO_GRAPHQL_JWT_ALGORITHM"])

        query = urlencode({"token": token})

        return f"/download?{query}"

    def pre_signed_url_create(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Get a presigned URL for creating a dataset.

        Returns:
            dict: A presigned URL for creating the dataset.
        """

        path = Path(filepath).resolve()

        ALLOWED_ROOTS = []

        for root in CONFIG["KEDRO_GRAPHQL_PRESIGNED_URL_UPLOAD_ALLOWED_ROOTS"]:
            ALLOWED_ROOTS.append(Path(root).resolve())
            print(f"Allowed root: {Path(root).resolve()}")

        if not any(path.is_relative_to(root) for root in ALLOWED_ROOTS):
            raise ValueError(
                f"Path {path} is not allowed. Allowed roots: {ALLOWED_ROOTS}"
            )

        # New unique path
        path, file = str(path).rsplit("/", 1)
        new_path = path + "/" + str(uuid.uuid4()) + "/" + file

        token = jwt.encode({
            "filepath": new_path,
            "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp())
        }, CONFIG["KEDRO_GRAPHQL_JWT_SECRET_KEY"], algorithm=CONFIG["KEDRO_GRAPHQL_JWT_ALGORITHM"])

        return {"url": "/upload", "fields": {"token": token}}
