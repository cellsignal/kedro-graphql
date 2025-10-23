from typing import List
from kedro.io import AbstractDataset
from strawberry.types import Info
from .base import SignedUrlProvider
from ..config import load_config
from .. permissions import get_permissions
from .local_file_provider import LocalFileProvider
from ..utils import parse_s3_filepath
from ..models import DataSet
from ..exceptions import DataSetConfigError, DataSetError
import boto3
from botocore.exceptions import ClientError
from ..logs.logger import logger

CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))
logger.info("{s} using permissions class: {d}".format(s=__name__, d=PERMISSIONS_CLASS))


class S3Provider(SignedUrlProvider):
    """
    Implementation of SignedUrlProvider for AWS S3.

    """

    @staticmethod
    def presigned_url(filepath: str, expires_in_sec: int) -> str | None:
        """
        Generate a signed URL for an S3 file.
        Args:
            filepath (str): The S3 file path in the format s3://bucket-name/key
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            Optional[str]: A signed URL for the S3 file.
        """
        logger.info(f"Signing S3 URL for filepath: {filepath}")
        bucket_name, key, filename = parse_s3_filepath(filepath)

        s3_client = boto3.client('s3')
        params = {
            'Bucket': bucket_name,
            'Key': f"{key}/{filename}" if key else filename
        }

        try:
            return s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in_sec
            )
        except ClientError as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None

    @staticmethod
    def presigned_post(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Generate a presigned POST URL for uploading to S3.
        Args:
            filepath (str): The S3 file path in the format s3://bucket-name/key
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
        Returns:
            Optional[dict]: A dictionary with the URL and form fields for the presigned POST.
        """
        logger.info(f"Creating presigned POST for S3 filepath: {filepath}")
        bucket_name, key, filename = parse_s3_filepath(str(filepath))

        s3_client = boto3.client('s3')
        try:
            return s3_client.generate_presigned_post(bucket_name,
                                                     f"{key}/{filename}",
                                                     Fields=None,
                                                     Conditions=None,
                                                     ExpiresIn=expires_in_sec)
        except ClientError as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None

    @staticmethod
    def read(info: Info, dataset: DataSet, expires_in_sec: int, partitions: list | None = None) -> str | List[str]:
        """
        Generate a signed URL S3 to download a file.

        Args:
            filepath (str): The S3 file path in the format s3://bucket-name/key
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
            partitions (list | None): Optional list of partitions in a PartitionedDataset.

        Returns:
            str | List[str]: download url with query parameters

            Example: https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time
        """
        c = dataset.parse_config()

        if c["type"] in ["partitions.PartitionedDataset"]:

            protocol, path = dataset.parse_path()
            if protocol == "file":
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={path}, protocol=file, using LocalFileProvider")

                return LocalFileProvider.read(info, dataset, expires_in_sec, partitions)

            elif protocol != "s3":

                raise DataSetConfigError(
                    "Invalid dataset configuration. Must have 'filepath' with 's3' protocol")
            else:
                if not partitions or len(partitions) == 0:
                    # if no partitions provided,
                    # need the list of files in the partitioned dataset to generate signed URLs for each partition
                    files = AbstractDataset.from_config(dataset.name, c).load()
                    files = [path + "/" + f + c.get("filename_suffix", "")
                             for f in files]
                else:
                    files = [path + "/" + partition + c.get("filename_suffix", "")
                             for partition in partitions]
                signed_urls = []
                for file in files:
                    logger.info(
                        f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={file}, protocol=s3, expires_in_sec={expires_in_sec}")

                    signed = S3Provider.presigned_url(
                        file, expires_in_sec)

                    signed_urls.append(signed)
                return signed_urls

        elif c["type"] in ["partitions.IncrementalDataset"]:
            raise DataSetError(
                "Signed URLs for reading IncrementalDatasets are not supported.")
        else:

            protocol, filepath = dataset.parse_filepath()
            if protocol == "file":
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=file, using LocalFileProvider")

                return LocalFileProvider.read(info, dataset, expires_in_sec, partitions)

            elif protocol != "s3":

                raise DataSetConfigError(
                    "Invalid dataset configuration. Must have 'filepath' with 's3' protocol")
            else:

                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=s3, expires_in_sec={expires_in_sec}")
                return S3Provider.presigned_url(
                    filepath, expires_in_sec)

    @staticmethod
    def create(info: Info, dataset: DataSet, expires_in_sec: int, partitions: list | None = None) -> dict | List[dict]:
        """
        Generate a signed URL S3 to upload a file.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset to create a signed URL for.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
            partitions (list | None): Optional list of partitions in a PartitionedDataset.

        Returns:
            dict | List[dict]: Dictionary with the URL to post to and form fields and values to submit with the POST. If an error occurs, returns None.

            Example:
                {
                    "url": "https://your-bucket-name.s3.amazonaws.com/",
                    "fields": {
                        "key": "your-object-key",
                        "AWSAccessKeyId": "your-access-key-id",
                        "x-amz-security-token": "your-security-token",
                        "policy": "your-policy",
                        "signature": "your-signature"
                    }
                }
        """
        c = dataset.parse_config()

        if c["type"] in ["partitions.PartitionedDataset"]:

            protocol, path = dataset.parse_path()
            if protocol == "file":
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={path}, protocol=file, using LocalFileProvider")

                return LocalFileProvider.create(info, dataset, expires_in_sec, partitions)

            elif protocol != "s3":

                raise DataSetConfigError(
                    "Invalid dataset configuration. Must have 'filepath' with 's3' protocol")
            else:
                if not partitions or len(partitions) == 0:
                    # if no partitions provided,
                    # need the list of files in the partitioned dataset to generate signed URLs for each partition
                    files = AbstractDataset.from_config(dataset.name, c).load()
                    files = [path + "/" + f + c.get("filename_suffix", "")
                             for f in files]
                else:
                    files = [path + "/" + partition + c.get("filename_suffix", "")
                             for partition in partitions]
                signed_urls = []
                for file in files:
                    logger.info(
                        f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={file}, protocol=s3, expires_in_sec={expires_in_sec}")

                    signed = S3Provider.presigned_post(
                        file, expires_in_sec)

                    signed_urls.append(signed)
                return signed_urls

        elif c["type"] in ["partitions.IncrementalDataset"]:
            raise DataSetError(
                "Signed URLs for reading IncrementalDatasets are not supported.")
        else:
            protocol, filepath = dataset.parse_filepath()

            if protocol == "file":
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=file, using LocalFileProvider")

                return LocalFileProvider.create(info, dataset, expires_in_sec, partitions)

            elif protocol != "s3":

                raise DataSetConfigError(
                    "Invalid dataset configuration. Must have 'filepath' with 's3' protocol")
            else:
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=create_dataset, dataset={dataset.name}, filepath=s3://{filepath}, protocol=s3, expires_in_sec={expires_in_sec}")

                return S3Provider.presigned_post(filepath, expires_in_sec)
