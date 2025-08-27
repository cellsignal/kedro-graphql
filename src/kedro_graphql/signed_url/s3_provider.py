from kedro.io.core import _parse_filepath
from strawberry.types import Info
from .base import SignedUrlProvider
from ..config import load_config
from .. permissions import get_permissions
from .local_file_provider import LocalFileProvider
from ..utils import parse_s3_filepath
from ..models import DataSet
import boto3
from botocore.exceptions import ClientError
import uuid
from ..logs.logger import logger
import json

CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PERMISSIONS_CLASS = get_permissions(CONFIG.get("KEDRO_GRAPHQL_PERMISSIONS"))
logger.info("{s} using permissions class: {d}".format(s=__name__, d=PERMISSIONS_CLASS))


class S3Provider(SignedUrlProvider):
    """
    Implementation of SignedUrlProvider for AWS S3.
    """
    @staticmethod
    def read(info: Info, dataset: DataSet, expires_in_sec: int) -> str | None:
        """
        Generate a signed URL S3 to download a file.

        Args:
            filepath (str): The S3 file path in the format s3://bucket-name/key
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            Optional[str]: download url with query parameters

            Example: https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time
        """
        try:
            c = json.loads(dataset.config)
            filepath = c.get("filepath", None)
            if not filepath:
                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' key")

            elif _parse_filepath(filepath)["protocol"] == "file":
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=file, using LocalFileProvider")

                return LocalFileProvider.read(info, dataset, expires_in_sec)

            elif _parse_filepath(filepath)["protocol"] != "s3":

                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' with 's3' protocol")
            else:

                bucket_name, key, filename = parse_s3_filepath(filepath)

                s3_client = boto3.client('s3')
                params = {
                    'Bucket': bucket_name,
                    'Key': f"{key}/{filename}" if key else filename
                }

                try:
                    response = s3_client.generate_presigned_url(
                        'get_object',
                        Params=params,
                        ExpiresIn=expires_in_sec
                    )
                except ClientError as e:
                    logger.error(f"Failed to generate signed URL: {e}")
                    return None
        except json.JSONDecodeError as e:
            raise ValueError(f"Unable to parse JSON in config: {e}")
        except Exception as e:
            raise ValueError(f"Invalid dataset configuration: {e}")
        logger.info(
            f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=s3, expires_in_sec={expires_in_sec}")
        return response

    @staticmethod
    def create(info: Info, dataset: DataSet, expires_in_sec: int) -> dict | None:
        """
        Generate a signed URL S3 to upload a file.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset to create a signed URL for.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            Optional[JSON]: Dictionary with the URL to post to and form fields and values to submit with the POST. If an error occurs, returns None.

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

        try:
            c = json.loads(dataset.config)
            filepath = c.get("filepath", None)
            if not filepath:
                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' key")

            elif _parse_filepath(filepath)["protocol"] == "file":
                logger.info(
                    f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=read_dataset, dataset={dataset.name}, filepath={filepath}, protocol=file, using LocalFileProvider")

                return LocalFileProvider.create(info, dataset, expires_in_sec)

            elif _parse_filepath(filepath)["protocol"] != "s3":

                raise ValueError(
                    "Invalid dataset configuration. Must have 'filepath' with 's3' protocol")
            else:
                bucket_name, key, filename = parse_s3_filepath(filepath)

                s3_client = boto3.client('s3')
                try:
                    response = s3_client.generate_presigned_post(bucket_name,
                                                                 f"{key}/{filename}",
                                                                 Fields=None,
                                                                 Conditions=None,
                                                                 ExpiresIn=expires_in_sec)
                except ClientError as e:
                    logger.error(f"Failed to generate /signed URL: {e}")
                    return None

        except json.JSONDecodeError as e:
            raise ValueError(f"Unable to parse JSON in config: {e}")
        except Exception as e:
            raise ValueError(f"Invalid dataset configuration: {e}")
        logger.info(
            f"user={PERMISSIONS_CLASS.get_user_info(info)['email']}, action=create_dataset, dataset={dataset.name}, filepath=s3://{bucket_name}/{key}/{filename}, protocol=s3, expires_in_sec={expires_in_sec}")
        return response
