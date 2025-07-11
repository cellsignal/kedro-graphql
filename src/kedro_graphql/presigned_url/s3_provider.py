from .base import PreSignedUrlProvider
from ...utils import parse_s3_filepath
import boto3
from botocore.exceptions import ClientError
import uuid
from ...logs.logger import logger


class S3PreSignedUrlProvider(PreSignedUrlProvider):
    """
    Implementation of PreSignedUrlProvider for AWS S3.
    """
    @staticmethod
    def pre_signed_url_read(filepath: str, expires_in_sec: int) -> str | None:
        """
        Generate a presigned URL S3 to download a file.

        Args:
            filepath (str): The S3 file path in the format s3://bucket-name/key
            expires_in_sec (int): The number of seconds the presigned URL should be valid for.

        Returns:
            Optional[str]: download url with query parameters

            Example: https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time
        """

        bucket_name, s3_key = parse_s3_filepath(filepath)

        s3_client = boto3.client('s3')
        params = {
            'Bucket': bucket_name,
            'Key': s3_key
        }

        try:
            response = s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in_sec
            )
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

        return response

    @staticmethod
    def pre_signed_url_create(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Generate a presigned URL S3 to upload a file.

        Args:
            filepath (str): The S3 file path in the format s3://bucket-name/key
            expires_in_sec (int): The number of seconds the presigned URL should be valid for.

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

        bucket_name, s3_key = parse_s3_filepath(filepath)

        s3_client = boto3.client('s3')
        try:
            response = s3_client.generate_presigned_post(bucket_name,
                                                         f"{uuid.uuid4()}/{s3_key}",
                                                         Fields=None,
                                                         Conditions=None,
                                                         ExpiresIn=expires_in_sec)
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

        return response
