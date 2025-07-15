import abc


class SignedUrlProvider(metaclass=abc.ABCMeta):
    """
    Abstract base class for providing signed URLs for reading and creating kedro datasets
    """

    @abc.abstractmethod
    def read(filepath: str, expires_in_sec: int) -> str | None:
        """
        Abstract method to get a signed URL for downloading a dataset.

        Args:
            filepath (str): The file path of the dataset.
            expires_in_sec (int): The number of seconds the presigned URL should be valid for.

        Returns:
            str | None: A signed URL for downloading the dataset.
        """
        pass

    @abc.abstractmethod
    def create(filepath: str, expires_in_sec: int) -> dict | None:
        """
        Abstract method to get a signed URL for uploading a dataset.

        Args:
            filepath (str): The file path of the dataset.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.

        Returns:
            dict | None: A dictionary with the URL to post to and form fields and values to submit with the POST.
        """
        pass
