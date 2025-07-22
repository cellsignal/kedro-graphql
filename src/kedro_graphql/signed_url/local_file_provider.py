import json
import jwt
from kedro.io.core import _parse_filepath
from strawberry.types import Info
from ..models import DataSet
from .base import SignedUrlProvider
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path
from ..permissions import get_permissions
from ..logs.logger import logger
from ..config import load_config

CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))
logger.info("{s} using permissions class: {d}".format(s=__name__, d=PERMISSIONS_CLASS))


class LocalFileProvider(SignedUrlProvider):
    """
    Implementation of SignedUrlProvider for a local file system.
    """

    def read(info: Info, dataset: DataSet, expires_in_sec: int) -> str | None:
        """
        Get a signed URL for reading a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset to read.
            expires_in_sec (int): The expiration time in seconds.

        Returns:
            str: A signed URL for reading the dataset.
        """
        try:
            c = json.loads(dataset.config)
            filepath = c.get("filepath", None)
            if not filepath:
                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' key")

            if _parse_filepath(filepath)["protocol"] != "file":
                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' with 'file' protocol")

            path = Path(filepath).resolve()

            payload = {
                "filepath": str(path),
                "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp()),
                "iat": int(datetime.now().timestamp())
            }

            token = jwt.encode(payload, CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                               algorithm=CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"])

            query = urlencode({"token": token})

            logger.info(
                f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=file, expires_in_sec={expires_in_sec}")
            return f"{CONFIG['KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL']}/download?{query}"
        except json.JSONDecodeError as e:
            raise ValueError(f"Unable to parse JSON in config: {e}")
        except Exception as e:
            raise ValueError(f"Invalid dataset configuration: {e}")

    def create(info: Info, dataset: DataSet, expires_in_sec: int) -> dict | None:
        """
        Get a signed URL for creating a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset to create a signed URL for.
            expires_in_sec (int): The expiration time in seconds.

        Returns:
            dict: A signed URL for creating the dataset.
        """
        try:
            c = json.loads(dataset.config)
            filepath = c.get("filepath", None)
            if not filepath:
                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' key")

            if _parse_filepath(filepath)["protocol"] != "file":
                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' with 'file' protocol")

            path = Path(filepath).resolve()

            token = jwt.encode(
                {"filepath": str(path), "exp": int(
                    (datetime.now() + timedelta(seconds=expires_in_sec)).timestamp())},
                CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_SECRET_KEY"],
                algorithm=CONFIG["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_JWT_ALGORITHM"])

            logger.info(
                f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=create_dataset, dataset={dataset.name}, filepath={str(path)}, protocol=s3, expires_in_sec={expires_in_sec}")

            return {"url": f"{CONFIG['KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_SERVER_URL']}/upload", "fields": {"token": token}}
        except json.JSONDecodeError as e:
            raise ValueError(f"Unable to parse JSON in config: {e}")
        except Exception as e:
            raise ValueError(f"Invalid dataset configuration: {e}")
