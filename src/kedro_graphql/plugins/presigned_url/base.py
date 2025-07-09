import abc


class PreSignedUrlProvider(metaclass=abc.ABCMeta):
    """
    Abstract base class for providing presigned URLs for kedro datasets
    """

    @abc.abstractmethod
    def pre_signed_url_read(filepath: str, expires_in_sec: int) -> str | None:
        """
        Abstract method to get a presigned URL for downloading a dataset.

        Args:
            filepath (str): The file path of the dataset.
            expires_in_sec (int): The number of seconds the presigned URL should be valid for.

        Returns:
            str | None: A presigned URL for downloading the dataset.
        """
        pass

    @abc.abstractmethod
    def pre_signed_url_create(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Abstract method to get a presigned URL for uploading a dataset.

        Args:
            filepath (str): The file path of the dataset.
            expires_in_sec (int): The number of seconds the presigned URL should be valid for.

        Returns:
            dict | None: A dictionary with the URL to post to and form fields and values to submit with the POST.
        """
        pass
