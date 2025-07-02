import json
from functools import reduce
from urllib.parse import urlparse


def merge(a, b, path=None):
    """
    Merges nested dictionaries recursively.  Merges b into a.
    """
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def merge_dicts(dicts):
    return reduce(merge, dicts)


def parse_s3_filepath(filepath: str) -> tuple[str, str]:
    """
    Parse the s3 bucket name and key from DataSet filepath field.

    Args:
        filepath (str): The S3 file path in the format s3://bucket-name/key

    Returns:
        tuple: A tuple containing the bucket name and the S3 key (object path).

    Raises:
        ValueError: If the filepath does not start with "s3://" or if the bucket name or S3 key is missing.
    """

    if not filepath.startswith("s3://"):
        raise ValueError("Invalid S3 path. Must start with 's3://'")

    parsed = urlparse(filepath)
    bucket_name = parsed.netloc
    s3_key = parsed.path.lstrip("/")

    if not bucket_name:
        raise ValueError("Invalid S3 path. Bucket name is missing.")
    if not s3_key:
        raise ValueError("Invalid S3 path. S3 key (object path) is missing.")

    return bucket_name, s3_key
