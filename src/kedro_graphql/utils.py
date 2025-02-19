from functools import reduce
from urllib.parse import urlparse
import json

def merge(a, b, path=None):
    "merges nested dictionaries recursively.  Merges b into a."
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def merge_dicts(dicts):
    return reduce(merge, dicts)

def parse_filepath_for_s3(config, s3_filepath):
    """
    Parse the s3 bucket name and key from DataSet filepath field.
    """
    if config:
        try:
            dataset_dict = json.loads(config)
            filepath = dataset_dict.get("filepath")
            if not filepath:
                raise ValueError("Invalid dataset configuration. Must have 'filepath' key")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config: {e}")
    elif s3_filepath:
        filepath = s3_filepath
    else:
        raise ValueError("Invalid dataset configuration. Must have 'filepath' key")

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
