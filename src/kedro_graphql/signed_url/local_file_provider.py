import json
from typing import List
import jwt
from kedro.io import AbstractDataset
from strawberry.types import Info
from ..models import DataSet, SignedUrl, SignedUrls, SignedUrlField
from .base import SignedUrlProvider
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path
from ..permissions import permission_class
from ..logs.logger import logger
from ..config import KedroGraphQLConfig
from ..exceptions import DataSetError

def _config(info: Info) -> KedroGraphQLConfig:
    return info.context.request.app.state.services.config


class LocalFileProvider(SignedUrlProvider):
    """
    Implementation of SignedUrlProvider for a local file system.
    """

    @staticmethod
    def sign_url(
        filepath: str | Path,
        expires_in_sec: int,
        url: str,
        config: KedroGraphQLConfig,
    ) -> dict:
        """
        Generate a signed URL for a local file.

        Args:
            filepath (pathlib.Path | str): The local file path.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
            url (str): The base URL for the signed URL.

        Returns:
            dict: A signed URL for the local file e.g. {"url": "http://example.com/download?token=abc123", "fields": {"token": "abc123"}}
        """
        if isinstance(filepath, str):
            path = Path(filepath).resolve()
        else:
            path = filepath.resolve()

        payload = {
            "filepath": str(path),
            "exp": int((datetime.now() + timedelta(seconds=expires_in_sec)).timestamp()),
            "iat": int(datetime.now().timestamp())
        }

        token = jwt.encode(
            payload,
            config.local_file_provider_jwt_secret_key,
            algorithm=config.local_file_provider_jwt_algorithm,
        )

        return SignedUrl(url=url, file=path.name, fields=[SignedUrlField(name="token", value=token)])

    @staticmethod
    def read(info: Info, dataset: DataSet, expires_in_sec: int, partitions: list | None = None) -> SignedUrl | SignedUrls:
        """
        Get a signed URL for reading a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset to read.
            expires_in_sec (int): The expiration time in seconds.
            partitions (list | None): Optional list of partitions in a PartitionedDataset.

        Returns:
            str | List[str]: A signed URL for reading the dataset.

        Raises:
            DataSetError: If signed URLs for the dataset type are not supported.
        """
        c = dataset.parse_config()

        if c["type"] in ["partitions.PartitionedDataset"]:

            protocol, path = dataset.parse_path()
            path = Path(path)
            if not partitions or len(partitions) == 0:
                # if no partitions provided,
                # need the list of files in the partitioned dataset to generate signed URLs for each partition
                files = AbstractDataset.from_config(dataset.name, c).load()
                files = [str(path / f) + c.get("filename_suffix", "") for f in files]
            else:
                files = [str(path / partition) + c.get("filename_suffix", "")
                         for partition in partitions]
            signed_urls = []
            for file in files:
                logger.info(
                    f"user={permission_class(info).get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={file}, protocol=file, expires_in_sec={expires_in_sec}")

                signed = LocalFileProvider.sign_url(
                    file, expires_in_sec, f"{_config(info).local_file_provider_server_url}/download", _config(info))

                query = urlencode({"token": signed.get_field_value("token")})
                signed.url = f"{_config(info).local_file_provider_server_url}/download?{query}"
                signed_urls.append(signed)
            return SignedUrls(urls=signed_urls)

        elif c["type"] in ["partitions.IncrementalDataset"]:
            raise DataSetError(
                "Signed URLs for reading IncrementalDatasets are not supported.")
        else:
            protocol, filepath = dataset.parse_filepath()
            filepath = Path(filepath)

            logger.info(
                f"user={permission_class(info).get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=file, expires_in_sec={expires_in_sec}")
            signed = LocalFileProvider.sign_url(
                filepath, expires_in_sec, f"{_config(info).local_file_provider_server_url}/download", _config(info))

            query = urlencode({"token": signed.get_field_value("token")})
            signed.url = f"{_config(info).local_file_provider_server_url}/download?{query}"
            return signed

    @staticmethod
    def create(info: Info, dataset: DataSet, expires_in_sec: int, partitions: list | None = None) -> SignedUrl | SignedUrls:
        """
        Get a signed URL for creating a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset to create a signed URL for.
            expires_in_sec (int): The expiration time in seconds.
            partitions (list | None): Optional list of partitions in a PartitionedDataset.

        Returns:
            dict | List[dict]: A signed URL for creating the dataset.

        Raises:
            ValueError: If partitions are not provided for a PartitionedDataset.
            DataSetError: If signed URLs for the dataset type are not supported.
        """
        c = dataset.parse_config()
        if c["type"] in ["partitions.PartitionedDataset"]:
            if not partitions or len(partitions) == 0:
                raise ValueError(
                    "Partitions must be provided for PartitionedDataset")

            signed_urls = []
            protocol, path = dataset.parse_path()
            path = Path(path)
            for partition in partitions:
                filepath = str(path / partition) + c.get("filename_suffix", "")
                logger.info(
                    f"user={permission_class(info).get_user_info(info)['email']}, action=create_dataset, dataset={dataset.name}, filepath={str(filepath)}, protocol=file, expires_in_sec={expires_in_sec}")

                signed_urls.append(LocalFileProvider.sign_url(
                    filepath, expires_in_sec, f"{_config(info).local_file_provider_server_url}/upload", _config(info)))

            return SignedUrls(urls=signed_urls)
        elif c["type"] in ["partitions.IncrementalDataset"]:
            raise DataSetError(
                "Signed URLs for creating IncrementalDatasets are not supported.")
        else:
            protocol, filepath = dataset.parse_filepath()
            filepath = Path(filepath)
            logger.info(
                f"user={permission_class(info).get_user_info(info)['email']}, action=create_dataset, dataset={dataset.name}, filepath={str(filepath)}, protocol=file, expires_in_sec={expires_in_sec}")

            return LocalFileProvider.sign_url(filepath, expires_in_sec, f"{_config(info).local_file_provider_server_url}/upload", _config(info))
