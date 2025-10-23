import gql
import json
from functools import reduce
from graphql.language import print_ast
from importlib_resources import files
from typing import Any, Optional
from .models import Pipeline
from urllib.parse import urlparse
from .logs.logger import logger
from .exceptions import DataSetConfigError


def build_graphql_query(
    query_name: str, fragments: Optional[list] = None, query_file="queries.gql"
) -> str:

    query_path = files("kedro_graphql.static").joinpath(query_file)

    # ensure it exists
    if not query_path.exists():
        raise FileNotFoundError(
            f"Query file {query_file} not found. Ensure it exists in kedro_graphql.static"
        )

    with open(query_path, "r") as f:
        document = gql.gql(f.read())  # Parse the entire document

    outstr = ""

    # # Iterate through definitions and extract named operations
    for definition in document.definitions:
        if hasattr(definition, "name") and definition.name.value == query_name:
            outstr += print_ast(definition) + "\n"

    if not outstr:
        raise ValueError(f"Query {query_name} not found in {query_file}")

    if fragments:
        count = 0
        for definition in document.definitions:
            if hasattr(definition, "name") and definition.name.value in fragments:
                outstr += print_ast(definition) + "\n"
                count += 1
        if count != len(fragments):
            raise ValueError(f"Not all fragments {fragments} found in {query_file}")

    return outstr


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
        tuple: A tuple containing the bucket name, the S3 prefix, and the S3 object name.

    Raises:
        ValueError: If the filepath does not start with "s3://" or if the bucket name or S3 key is missing.
    """

    if not filepath.startswith("s3://"):
        raise ValueError("Invalid S3 path. Must start with 's3://'")

    parsed = urlparse(filepath)
    bucket_name = parsed.netloc
    s3_key = parsed.path.lstrip("/")
    filename = s3_key.split("/")[-1]
    s3_key = "/".join(s3_key.split("/")[:-1])  # Remove the filename from the key

    if not bucket_name:
        raise ValueError("Invalid S3 path. Bucket name is missing.")
    # if not s3_key:
    #    raise ValueError("Invalid S3 path. S3 key (object path) is missing.")

    return bucket_name, s3_key, filename


def add_param_to_feed_dict(feed_dict, param_name: str, param_value: Any, add_prefix=True) -> None:
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


def generate_unique_paths(pipeline: Pipeline, datasets: list) -> Pipeline:
    """Modifies filepaths in the pipeline's data catalog to ensure they are unique.

    Args:
        pipeline (Pipeline): The Kedro pipeline to scope filepaths for.
        datasets (list): List of dataset names to create unique filepaths for.

    Returns:
        Pipeline: The same pipeline with a modified data catalog containing unique filepaths for specified datasets.
    Raises:
        DataSetConfigError: If a dataset does not have a 'filepath' or 'path' key in its configuration.
    """
    for d in pipeline.data_catalog:
        if d.name in datasets:
            c = json.loads(d.config)
            if c.get("filepath", None):
                filepath = c["filepath"]
                parts = filepath.rsplit("/", 1)
                new_path = parts[0] + "/" + pipeline.id + "/" + parts[1]
                c["filepath"] = new_path
                logger.info(
                    f"Modifying dataset {d.name} filepath to {new_path} to ensure uniqueness.")
                d.config = json.dumps(c)
            elif c.get("path", None):
                path = c["path"]
                parts = path.rsplit("/", 1)
                new_path = parts[0] + "/" + pipeline.id + "/" + parts[1]
                c["path"] = new_path
                logger.info(
                    f"Modifying dataset {d.name} path to {new_path} to ensure uniqueness.")
                d.config = json.dumps(c)
            else:
                raise DataSetConfigError(
                    f"Dataset {d.name} does not have a 'filepath' or 'path' key in its configuration.")
        else:
            logger.info(
                f"Dataset {d.name} not in specified datasets list, skipping filepath modification.")
    return pipeline
