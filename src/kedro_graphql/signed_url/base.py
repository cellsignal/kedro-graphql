import abc
from ..models import DataSet
from strawberry.types import Info


class SignedUrlProvider(metaclass=abc.ABCMeta):
    """
    Abstract base class for providing signed URLs for reading and creating kedro datasets
    """

    @abc.abstractmethod
    def read(info: Info, dataset: DataSet, expires_in_sec: int, partitions: list | None = None) -> str | None:
        """
        Abstract method to get a signed URL for downloading a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset for which to create a signed URL.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
            partitions (list | None): Optional list of partitions for datasets with multiple files e.g. a PartitionedDataset.

        Returns:
            str | None: A signed URL for downloading the dataset.
        """
        pass

    @abc.abstractmethod
    def create(info: Info, dataset: DataSet, expires_in_sec: int, partitions: list | None = None) -> dict | None:
        """
        Abstract method to get a signed URL for uploading a dataset.

        Args:
            info (Info): Strawberry GraphQL Info object.
            dataset (DataSet): The dataset for which to create a signed URL.
            expires_in_sec (int): The number of seconds the signed URL should be valid for.
            partitions (list | None): Optional list of partitions for datasets with multiple files e.g. a PartitionedDataset.

        Returns:
            dict | None: A dictionary with the URL to post to and form fields and values to submit with the POST.
        """
        pass
