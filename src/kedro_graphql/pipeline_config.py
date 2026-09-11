"""Pipeline-aware catalog resolution and validation."""

import json
from collections.abc import Mapping

from kedro.io import AbstractDataset, DataCatalog, MemoryDataset
from kedro.io.core import DatasetError
from omegaconf import OmegaConf

from .exceptions import InvalidPipeline


_CREDENTIAL_FIELDS = {
    "access_key",
    "access_token",
    "api_key",
    "apikey",
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "client_secret",
    "password",
    "passwd",
    "private_key",
    "refresh_token",
    "secret",
    "secret_key",
    "token",
}


def validate_configuration_boundary(catalog, parameters, max_bytes):
    """Reject inline credentials and configuration too large for transport."""

    def visit(value, path):
        if isinstance(value, Mapping):
            for key, item in value.items():
                normalized = str(key).lower().replace("-", "_")
                item_path = f"{path}.{key}"
                if normalized in _CREDENTIAL_FIELDS:
                    raise InvalidPipeline(
                        f"Credential-bearing configuration is not allowed: {item_path}"
                    )
                if normalized == "credentials" and not isinstance(item, str):
                    raise InvalidPipeline(
                        f"Inline credentials are not allowed: {item_path}"
                    )
                visit(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    payload = {"data_catalog": catalog, "parameters": parameters}
    visit(payload, "configuration")
    try:
        size = len(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        )
    except (TypeError, ValueError) as error:
        raise InvalidPipeline(f"Configuration is not JSON serializable: {error}") from error
    if size > max_bytes:
        raise InvalidPipeline(
            f"Resolved pipeline configuration is {size} bytes; limit is {max_bytes} bytes."
        )


def merge_parameters(defaults, overrides):
    """Apply dotted request parameters to nested server configuration."""
    merged = OmegaConf.create(defaults)
    for name, value in overrides.items():
        OmegaConf.update(merged, name, value, merge=True)
    return OmegaConf.to_container(merged, resolve=True)


def normalize_pipeline_config(pipeline, catalog, parameters):
    """Resolve catalog patterns and retain only config used by ``pipeline``."""
    dataset_names = sorted(
        name
        for name in pipeline.all_inputs() | pipeline.all_outputs()
        if not name.startswith("params:") and name != "parameters"
    )
    candidates = {
        name: config
        for name, config in catalog.items()
        if "{" in name or name in dataset_names
    }
    try:
        resolver = DataCatalog.from_config(catalog=candidates).config_resolver
        resolved = {
            name: config
            for name in dataset_names
            if (config := resolver.resolve_pattern(name))
        }
        # Instantiate the concrete, relevant configurations now so invalid staged
        # pipelines fail before they are persisted.
        DataCatalog.from_config(catalog=resolved)
    except DatasetError as error:
        raise InvalidPipeline(f"Invalid pipeline catalog: {error}") from error

    parameter_inputs = pipeline.all_inputs()
    if "parameters" in parameter_inputs:
        filtered_parameters = parameters
    else:
        required = {
            name.removeprefix("params:")
            for name in parameter_inputs
            if name.startswith("params:")
        }
        filtered_parameters = {}
        for name in required:
            try:
                filtered_parameters[name] = _parameter_value(parameters, name)
            except KeyError:
                pass

    sources = {
        name: name if name in candidates else resolver.match_pattern(name)
        for name in resolved
    }
    return resolved, filtered_parameters, sources


def _parameter_value(parameters, name):
    if name in parameters:
        return parameters[name]
    value = parameters
    for part in name.split("."):
        value = value[part]
    return value


def pipeline_slice_args(slices=None):
    """Translate GraphQL slices into Kedro filter arguments."""
    filters = {}
    for item in slices or []:
        slice_type = item["slice"].lower()
        filters[slice_type] = (
            item["args"][0] if slice_type == "node_namespace" else item["args"]
        )
    return filters


def filter_pipeline(pipeline, slices=None):
    """Apply explicit GraphQL pipeline slices."""
    return pipeline.filter(**pipeline_slice_args(slices))


def filter_only_missing_pipeline(pipeline, catalog):
    """Build Kedro's dynamic ``only_missing`` execution DAG."""
    free_outputs = pipeline.outputs() - set(catalog.list())
    missing = {name for name in catalog.list() if not catalog.exists(name)}
    to_build = free_outputs | missing
    filtered = pipeline.only_nodes_with_outputs(*to_build) + pipeline.from_inputs(*to_build)

    unregistered = pipeline.datasets() - set(catalog.list())
    producers = pipeline.only_nodes_with_outputs(*unregistered)
    return filtered + producers.to_outputs(*(filtered.inputs() & unregistered))


def validate_pipeline_config(
    pipeline, catalog, parameters, supports_memory_datasets=True
):
    """Validate configuration required by the actual execution DAG."""
    missing_inputs = sorted(
        name
        for name in pipeline.inputs()
        if not name.startswith("params:")
        and name != "parameters"
        and name not in catalog
    )
    missing_parameters = sorted(
        name.removeprefix("params:")
        for name in pipeline.inputs()
        if name.startswith("params:")
        and not _has_parameter(parameters, name.removeprefix("params:"))
    )
    if missing_inputs or missing_parameters:
        details = []
        if missing_inputs:
            details.append(f"datasets: {', '.join(missing_inputs)}")
        if missing_parameters:
            details.append(f"parameters: {', '.join(missing_parameters)}")
        raise InvalidPipeline("Missing pipeline inputs (" + "; ".join(details) + ").")

    if not supports_memory_datasets:
        missing_or_memory = []
        for name in sorted(pipeline.datasets()):
            if name.startswith("params:") or name == "parameters":
                continue
            config = catalog.get(name)
            if not config or isinstance(
                AbstractDataset.from_config(name, config), MemoryDataset
            ):
                missing_or_memory.append(name)
        if missing_or_memory:
            raise InvalidPipeline(
                "Runner does not support memory datasets; configure persistent datasets for: "
                + ", ".join(missing_or_memory)
                + "."
            )


def _has_parameter(parameters, name):
    try:
        _parameter_value(parameters, name)
        return True
    except (KeyError, TypeError):
        return False
