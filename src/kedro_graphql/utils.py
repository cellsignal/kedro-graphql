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

def json_to_dotlist(cfg, prefix=""):
    """
    Recursively converts a JSON object into a list of dot-separated key=value pairs, 
    preserving quotes for string values.

    Args:
        cfg (dict): The JSON object (dictionary) to be flattened into dot notation.
        prefix (str, optional): The prefix to maintain hierarchy in keys (used for recursion). 
                                Defaults to an empty string.

    Returns:
        list: A list of strings where each element follows the format "key.subkey=value".
              String values are enclosed in single quotes ('') to preserve them.
    
    Example:
        >>> config = {
        ...     "model_options": {
        ...         "model_params": {
        ...             "learning_date": "2023-11-01",
        ...             "training_date": "2023-11-01",
        ...             "data_ratio": 14
        ...         }
        ...     }
        ... }
        >>> json_to_dotlist(config)
        [
            "model_options.model_params.learning_date='2023-11-01'",
            "model_options.model_params.training_date='2023-11-01'",
            "model_options.model_params.data_ratio=14"
        ]
    """
    dotlist = []
    for key, value in cfg.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):  # If nested, recurse
            dotlist.extend(json_to_dotlist(value, full_key))
        elif isinstance(value, str):
            dotlist.append(f"{full_key}='{value}'")
        else:
            dotlist.append(f"{full_key}={value}")
    return dotlist
