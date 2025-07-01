import abc


class PreSignedUrlProvider(metaclass=abc.ABCMeta):
    """
    Abstract base class for providing presigned URLs for kedro datasets
    """

    @abc.abstractmethod
    def pre_signed_url_read(config: dict) -> str | None:
        """
        Abstract method to get a presigned URL for downloading a dataset.

        Args:
            config (dict): The configuration dictionary.

        Returns:
            str: A presigned URL for downloading the dataset.
        """
        pass

    @abc.abstractmethod
    def pre_signed_url_create(config: dict) -> dict | None:
        """
        Abstract method to get a presigned URL for uploading a dataset.

        Args:
            config (dict): The configuration dictionary.

        Returns:
            PresignedUploadUrl | None: A presigned URL for uploading the dataset with the appropriate fields.
        """
        pass
