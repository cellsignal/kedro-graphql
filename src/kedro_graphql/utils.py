import json
from functools import reduce
from urllib.parse import urlparse
from typing import Any

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


def parse_s3_filepath(config):
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


def add_param_to_feed_dict(feed_dict, param_name: str, param_value: Any, add_prefix = True) -> None:
    """Context-free version of utility found inside KedroContext._get_feed_dict method. Option to add params: prefix if desired.

    Example:

        >>> param_name = "a"
        >>> param_value = {"b": 1}
        >>> feed_dict = {}
        >>> _add_param_to_feed_dict(feed_dict, param_name, param_value)
        >>> assert feed_dict["params:a"] == {"b": 1}
        >>> assert feed_dict["params:a.b"] == 1
    """
    key = f"params:{param_name}" if add_prefix else param_name
    feed_dict[key] = param_value
    if isinstance(param_value, dict):
        for key, val in param_value.items():
            add_param_to_feed_dict(feed_dict, f"{param_name}.{key}", val)


