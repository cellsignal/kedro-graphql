"""GraphQL-backed pipeline submission planning and validation."""

from __future__ import annotations

import copy
import json
import math
from importlib import import_module
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse
from uuid import uuid4

import boto3
import jwt
import strawberry
from botocore.exceptions import BotoCoreError, ClientError
from strawberry.scalars import JSON
from kedro.io import AbstractDataset, MemoryDataset, DatasetError
from kedro.io.core import parse_dataset_definition
from kedro_datasets.partitions import PartitionedDataset

from .exceptions import InvalidPipeline
from .pipeline_visibility import require_pipeline_submission_name_allowed
from .models import (
    DataSetInput,
    Node,
    ParameterInput,
    ParameterType,
    PipelineInput,
    PipelineInputStatus,
    PipelineSlice,
    SignedUrl,
    SignedUrlField,
)
from .pipeline_config import filter_pipeline, normalize_pipeline_config
from .project import load_pipeline_configuration
from .signed_url.s3_provider import S3Provider
from .autocomplete import DatasetInputContext, InputAutocomplete, find_input_provider


@strawberry.enum
class SubmissionValueType(Enum):
    NULL = "NULL"
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    ARRAY = "ARRAY"
    OBJECT = "OBJECT"


@strawberry.enum
class SubmissionInputMethod(Enum):
    S3_URI = "S3_URI"
    UPLOAD = "UPLOAD"


@strawberry.enum
class SubmissionDatasetKind(Enum):
    SINGLE_FILE = "SINGLE_FILE"
    PARTITIONED = "PARTITIONED"
    COLLECTION = "COLLECTION"


@strawberry.type
class SubmissionParameter:
    path: str
    segments: list[str]
    type: SubmissionValueType
    default_value: JSON | None
    editable: bool
    reason: str | None = None
    visible_in_form: bool = True


@strawberry.type
class SubmissionFolderUploadLimits:
    max_files: int
    max_total_bytes: float
    max_file_bytes: float


@strawberry.type
class SubmissionSuffixReplacement:
    from_suffix: str
    to_suffix: str


@strawberry.type
class SubmissionRegexSubstitution:
    pattern: str
    replacement: str


@strawberry.type
class SubmissionInputDerivation:
    source_dataset: str
    append_suffix: str | None = None
    replace_suffix: SubmissionSuffixReplacement | None = None
    regex_sub: SubmissionRegexSubstitution | None = None


@strawberry.type
class SubmissionDataset:
    name: str
    dataset_type: str
    kind: SubmissionDatasetKind
    required: bool
    methods: list[SubmissionInputMethod]
    supported: bool
    reason: str | None = None
    autocomplete: InputAutocomplete | None = None
    filename_suffix: str | None = None
    folder_upload_limits: SubmissionFolderUploadLimits | None = None
    derivation: SubmissionInputDerivation | None = None


@strawberry.type
class SubmissionOutput:
    name: str
    dataset_type: str
    free: bool
    managed: bool


@strawberry.type
class PipelineSubmissionForm:
    pipeline_name: str
    runner: str
    nodes: list[Node]
    inputs: list[SubmissionDataset]
    parameters: list[SubmissionParameter]
    outputs: list[SubmissionOutput]
    max_batch_size: int
    batch_limit_reason: str | None = None


@strawberry.type
class SubmissionValidationError:
    path: str | None
    message: str


@strawberry.type
class ResolvedSubmissionInput:
    name: str
    s3_uri: str


@strawberry.type
class SubmissionValidationResult:
    valid: bool
    errors: list[SubmissionValidationError]
    resolved_inputs: list[ResolvedSubmissionInput] = strawberry.field(default_factory=list)


@strawberry.type
class SubmissionUpload:
    upload_id: str
    url: str
    file: str
    fields: list[SignedUrlField]
    expires_at: datetime
    max_bytes: int


@strawberry.input
class SubmissionFolderFileInput:
    relative_path: str
    size: float


@strawberry.type
class SubmissionFolderFileUpload:
    relative_path: str
    upload: SubmissionUpload


@strawberry.type
class SubmissionFolderUpload:
    upload_id: str
    files: list[SubmissionFolderFileUpload]


@strawberry.input
class SubmissionParameterInput:
    segments: list[str]
    type: SubmissionValueType
    value: JSON | None = None


@strawberry.input
class SubmissionDatasetInput:
    name: str
    method: SubmissionInputMethod
    s3_uri: str | None = None
    s3_uris: list[str] | None = None
    upload_id: str | None = None


@strawberry.input
class PipelineSubmissionInput:
    name: str
    slices: list[PipelineSlice] = strawberry.field(default_factory=list)
    parameters: list[SubmissionParameterInput] = strawberry.field(default_factory=list)
    inputs: list[SubmissionDatasetInput] = strawberry.field(default_factory=list)


@dataclass(frozen=True)
class _ParameterSpec:
    segments: tuple[str, ...]
    value_type: SubmissionValueType
    default: Any
    editable: bool
    reason: str | None = None


_MISSING = object()


def _slice_payload(slices: list[PipelineSlice] | None) -> list[dict[str, Any]]:
    """Serialize GraphQL slices for pipeline filtering."""
    payload = []
    for item in slices or []:
        value = item.slice.value if hasattr(item.slice, "value") else item.slice
        payload.append({"slice": str(value).lower(), "args": list(item.args)})
    return payload


def _simple(value: Any) -> bool:
    """Return whether a value is a supported scalar."""
    return value is None or type(value) in {bool, str, int, float}


def _value_type(value: Any) -> SubmissionValueType:
    """Classify a Python value for submission input."""
    if value is None:
        return SubmissionValueType.NULL
    if type(value) is bool:
        return SubmissionValueType.BOOLEAN
    if type(value) is str:
        return SubmissionValueType.STRING
    if type(value) is int:
        return SubmissionValueType.INTEGER
    if type(value) is float:
        return SubmissionValueType.FLOAT
    if type(value) is list:
        return SubmissionValueType.ARRAY
    return SubmissionValueType.OBJECT


def _flatten_parameter(
    value: Any,
    segments: tuple[str, ...],
    specs: dict[tuple[str, ...], _ParameterSpec],
) -> None:
    """Collect editable leaf parameters from nested values."""
    if isinstance(value, Mapping):
        if not value:
            specs[segments] = _ParameterSpec(
                segments,
                SubmissionValueType.OBJECT,
                value,
                False,
                "Mapping parameters are not editable as one value.",
            )
            return
        for key, child in value.items():
            _flatten_parameter(child, (*segments, str(key)), specs)
        return
    if isinstance(value, list):
        editable = all(_simple(item) for item in value)
        specs[segments] = _ParameterSpec(
            segments,
            SubmissionValueType.ARRAY,
            value,
            editable,
            None if editable else "Only arrays of simple values are editable.",
        )
        return
    specs[segments] = _ParameterSpec(segments, _value_type(value), value, True)


def _resolve_parameter(parameters: Mapping[str, Any], path: str) -> tuple[Any, tuple[str, ...]]:
    """Resolve a dotted parameter path."""
    if path in parameters:
        return parameters[path], (path,)
    value: Any = parameters
    segments = tuple(path.split("."))
    for segment in segments:
        if not isinstance(value, Mapping) or segment not in value:
            return _MISSING, segments
        value = value[segment]
    return value, segments


def _parameter_specs(selected, parameters: Mapping[str, Any]) -> dict[tuple[str, ...], _ParameterSpec]:
    """Build parameter specs required by the selected pipeline."""
    specs: dict[tuple[str, ...], _ParameterSpec] = {}
    required = sorted(
        name.removeprefix("params:")
        for name in selected.inputs()
        if name.startswith("params:") and name != "params:"
    )
    for path in required:
        value, segments = _resolve_parameter(parameters, path)
        if value is _MISSING:
            specs[segments] = _ParameterSpec(
                segments,
                SubmissionValueType.NULL,
                None,
                False,
                "The server did not provide a default value.",
            )
        else:
            _flatten_parameter(
                value,
                segments,
                specs,
            )
    return specs


def _parameter_visible(path: str, allowlist: list[str] | None, disallowlist: list[str]) -> bool:
    """Use the deepest matching visibility rule; disallow wins ties."""
    allow_depth = max(
        (rule.count(".") for rule in allowlist or [] if path == rule or path.startswith(rule + ".")),
        default=-1,
    )
    disallow_depth = max(
        (rule.count(".") for rule in disallowlist if path == rule or path.startswith(rule + ".")),
        default=-1,
    )
    if allow_depth == disallow_depth == -1:
        return allowlist is None
    return allow_depth > disallow_depth


def _collection_location_key(config: Mapping[str, Any]) -> str | None:
    """Read an inherited dataset capability without instantiating the dataset."""
    if not config.get("type"):
        return None
    dataset_class, _ = parse_dataset_definition(dict(config))
    key = getattr(dataset_class, "submission_input_location_key", None)
    return "paths" if key == "paths" else None


def _dataset_kind(config: Mapping[str, Any]) -> SubmissionDatasetKind:
    """Classify the supported submission input shape."""
    if _collection_location_key(config):
        return SubmissionDatasetKind.COLLECTION
    if config.get("type") and issubclass(parse_dataset_definition(dict(config))[0], PartitionedDataset):
        return SubmissionDatasetKind.PARTITIONED
    return SubmissionDatasetKind.SINGLE_FILE


def _dataset_location_key(config: Mapping[str, Any]) -> str | None:
    """Return the catalog key containing dataset locations."""
    if _collection_location_key(config):
        return "paths"
    if isinstance(config.get("filepath"), str):
        return "filepath"
    if isinstance(config.get("path"), str):
        return "path"
    return None


def _upload_root(config, name):
    return config.pipeline_submission_upload_roots.get(name) or config.pipeline_submission_upload_root


def _upload_root_is_usable(config) -> bool:
    """Check whether the configured upload root is usable."""
    root = config.pipeline_submission_upload_root
    if not root:
        return False
    if root.startswith("s3://"):
        parsed = urlparse(root)
        return bool(parsed.netloc)
    root_path = Path(root).resolve()
    allowed_roots = [Path(item).resolve() for item in config.local_file_provider_upload_allowed_roots]
    return any(root_path.is_relative_to(allowed) for allowed in allowed_roots)


def _dataset_descriptor(
    name: str, config: Mapping[str, Any] | None, server_config
) -> SubmissionDataset:
    """Describe how a dataset can be supplied to a submission."""
    if not config:
        return SubmissionDataset(
            name=name,
            dataset_type="unknown",
            kind=SubmissionDatasetKind.SINGLE_FILE,
            required=True,
            methods=[],
            supported=False,
            reason="No server catalog configuration is available for this input.",
        )
    dataset_type = str(config.get("type", "unknown"))
    kind = _dataset_kind(config)
    if _dataset_location_key(config) is None:
        return SubmissionDataset(
            name=name,
            dataset_type=dataset_type,
            kind=kind,
            required=True,
            methods=[],
            supported=False,
            reason="This dataset has no server-configured file location.",
        )
    methods = []
    if server_config.pipeline_submission_s3_allowed_prefixes:
        methods.append(SubmissionInputMethod.S3_URI)
    if kind is not SubmissionDatasetKind.COLLECTION and _upload_root_is_usable(server_config):
        methods.append(SubmissionInputMethod.UPLOAD)
    if not methods:
        return SubmissionDataset(
            name=name,
            dataset_type=dataset_type,
            kind=kind,
            required=True,
            methods=[],
            supported=False,
            reason="No supported input method is configured on this server.",
        )
    return SubmissionDataset(
        name=name,
        dataset_type=dataset_type,
        kind=kind,
        required=True,
        methods=methods,
        supported=True,
        filename_suffix=config.get("filename_suffix", "") if kind is SubmissionDatasetKind.PARTITIONED else None,
        folder_upload_limits=SubmissionFolderUploadLimits(
            max_files=server_config.pipeline_submission_partition_upload_max_files,
            max_total_bytes=server_config.pipeline_submission_partition_upload_max_size_mb * 1024 * 1024,
            max_file_bytes=_upload_max_bytes(server_config),
        ) if kind is SubmissionDatasetKind.PARTITIONED and SubmissionInputMethod.UPLOAD in methods else None,
    )


def _form_context(services, name: str, slices: list[PipelineSlice] | None):
    """Load and normalize the selected pipeline context."""
    require_pipeline_submission_name_allowed(services.config, name)
    if name not in services.metadata.pipelines:
        raise InvalidPipeline(f"Pipeline {name} does not exist in the project.")
    selected = filter_pipeline(services.metadata.pipelines[name], _slice_payload(slices))
    catalog, parameters = load_pipeline_configuration(
        services.metadata, services.config, name
    )
    resolved_catalog, _, _ = normalize_pipeline_config(selected, catalog, parameters)
    return selected, catalog, resolved_catalog, parameters


def build_submission_form(services, name: str, slices: list[PipelineSlice] | None = None) -> PipelineSubmissionForm:
    """Build submission metadata for a selected pipeline."""
    selected, catalog, resolved_catalog, parameters = _form_context(services, name, slices)
    produced = set(selected.outputs())
    free_inputs = sorted(
        dataset
        for dataset in selected.inputs() - produced
        if not dataset.startswith("params:") and dataset != "parameters"
    )
    upload_config = services.config.model_copy(update={
        "pipeline_submission_upload_root": _upload_root(services.config, name),
    })
    inputs = [
        _dataset_descriptor(
            name,
            resolved_catalog.get(name) or catalog.get(name),
            upload_config,
        )
        for name in free_inputs
    ]
    input_specs = {item.name: item for item in inputs}
    for rule in services.config.dataset_input_derivations:
        if rule.pipeline_name != name or rule.dataset_name not in input_specs or rule.source_dataset not in input_specs:
            continue
        target, source = input_specs[rule.dataset_name], input_specs[rule.source_dataset]
        if target.kind is not SubmissionDatasetKind.SINGLE_FILE or source.kind is not SubmissionDatasetKind.SINGLE_FILE:
            raise InvalidPipeline("Dataset input derivations require single-file source and target datasets.")
        target.derivation = SubmissionInputDerivation(
            source_dataset=rule.source_dataset, append_suffix=rule.append_suffix,
            replace_suffix=SubmissionSuffixReplacement(
                from_suffix=rule.replace_suffix.from_suffix, to_suffix=rule.replace_suffix.to_suffix,
            ) if rule.replace_suffix else None,
            regex_sub=SubmissionRegexSubstitution(
                pattern=rule.regex_sub.pattern, replacement=rule.regex_sub.replacement,
            ) if rule.regex_sub else None,
        )
    for descriptor in inputs:
        if descriptor.supported:
            context = DatasetInputContext(name, descriptor.name, resolved_catalog.get(descriptor.name) or catalog.get(descriptor.name) or {}, tuple(slices or []), None)
            provider = find_input_provider(services, context, [method.value for method in descriptor.methods])
            if provider is not None:
                descriptor.autocomplete = InputAutocomplete(method=provider.method)
    specs = _parameter_specs(selected, parameters)
    allowlist = services.config.pipeline_submission_parameter_allowlists.get(name)
    disallowlist = services.config.pipeline_submission_parameter_disallowlists.get(name, [])
    parameter_rows = []
    for spec in specs.values():
        path = ".".join(spec.segments)
        visible_in_form = _parameter_visible(path, allowlist, disallowlist)
        if not visible_in_form and _resolve_parameter(parameters, path)[0] is _MISSING:
            raise InvalidPipeline(
                f"Hidden parameter {path!r} for pipeline {name!r} has no server default."
            )
        parameter_rows.append(
            SubmissionParameter(
                path=path,
                segments=list(spec.segments),
                type=spec.value_type,
                default_value=spec.default,
                editable=spec.editable,
                reason=spec.reason,
                visible_in_form=visible_in_form,
            )
        )
    parameter_rows.sort(key=lambda item: item.path)
    outputs = [
        SubmissionOutput(
            name=dataset,
            dataset_type=str(
                (resolved_catalog.get(dataset) or catalog.get(dataset) or {}).get(
                    "type", "unknown"
                )
            ),
            free=dataset in selected.outputs(),
            managed=_dataset_location_key(resolved_catalog.get(dataset) or catalog.get(dataset) or {})
            in {"filepath", "path"},
        )
        for dataset in sorted(selected.all_outputs())
        if not dataset.startswith("params:") and dataset != "parameters"
    ]
    unsafe_outputs = [
        output.name for output in outputs
        if not output.managed
        and (config := resolved_catalog.get(output.name))
        and not isinstance(AbstractDataset.from_config(output.name, config), MemoryDataset)
    ]
    max_batch_size = services.config.pipeline_submission_batch_max_sizes.get(
        name, services.config.pipeline_submission_batch_max_size
    )
    batch_limit_reason = None
    if unsafe_outputs:
        max_batch_size = 1
        batch_limit_reason = "Outputs cannot be isolated for multiple runs: " + ", ".join(unsafe_outputs)
    nodes = [
        Node(name=node.name, inputs=node.inputs, outputs=node.outputs, tags=node.tags)
        for node in selected.nodes
    ]
    return PipelineSubmissionForm(
        pipeline_name=name,
        runner=services.config.pipeline_runners.get(name) or services.config.runner,
        nodes=nodes,
        inputs=inputs,
        parameters=parameter_rows,
        outputs=outputs,
        max_batch_size=max_batch_size,
        batch_limit_reason=batch_limit_reason,
    )


def _validate_parameter_value(value: Any, value_type: SubmissionValueType) -> bool:
    """Check a value against its declared submission type."""
    if value_type is SubmissionValueType.NULL:
        return value is None
    if value_type is SubmissionValueType.BOOLEAN:
        return type(value) is bool
    if value_type is SubmissionValueType.STRING:
        return type(value) is str
    if value_type is SubmissionValueType.INTEGER:
        return type(value) is int
    if value_type is SubmissionValueType.FLOAT:
        return type(value) is int or (type(value) is float and math.isfinite(value))
    if value_type is SubmissionValueType.ARRAY:
        return type(value) is list and all(_simple(item) for item in value)
    return False


def _set_parameter(parameters: dict[str, Any], segments: tuple[str, ...], value: Any) -> None:
    """Set a nested parameter value."""
    target = parameters
    for segment in segments[:-1]:
        child = target.get(segment)
        if not isinstance(child, dict):
            raise InvalidPipeline(f"Parameter path does not exist: {'.'.join(segments)}")
        target = child
    if not segments or segments[-1] not in target:
        raise InvalidPipeline(f"Parameter path does not exist: {'.'.join(segments)}")
    target[segments[-1]] = value


def _parameter_inputs(parameters: Mapping[str, Any]) -> list[ParameterInput]:
    """Convert parameter values to Kedro inputs."""
    result = []
    for name, value in parameters.items():
        if value is None or isinstance(value, (dict, list)):
            result.append(
                ParameterInput(name=name, value=json.dumps(value), type=ParameterType.JSON)
            )
        elif type(value) is bool:
            result.append(ParameterInput(name=name, value=str(value).lower(), type=ParameterType.BOOLEAN))
        elif type(value) is int:
            result.append(ParameterInput(name=name, value=str(value), type=ParameterType.INTEGER))
        elif type(value) is float:
            result.append(ParameterInput(name=name, value=str(value), type=ParameterType.FLOAT))
        elif type(value) is str:
            result.append(ParameterInput(name=name, value=value, type=ParameterType.STRING))
        else:
            raise InvalidPipeline(f"Unsupported parameter value at {name}")
    return result


def _s3_parts(uri: str) -> tuple[str, str]:
    """Parse and validate an S3 URI."""
    parsed = urlparse(uri)
    if (parsed.scheme != "s3" or not parsed.netloc or not parsed.path.strip("/")
            or parsed.query or parsed.fragment or "@" in parsed.netloc or ":" in parsed.netloc):
        raise InvalidPipeline("S3 inputs must be full s3://bucket/key URIs.")
    return parsed.netloc, parsed.path.lstrip("/")


def _within_s3_scope(uri: str, roots: list[str]) -> bool:
    """Check whether an S3 URI falls under a configured root."""
    normalized = uri.rstrip("/")
    return any(
        normalized == root.rstrip("/")
        or normalized.startswith(root.rstrip("/") + "/")
        for root in roots
    )


def _check_s3_uri(config, uri: str) -> str:
    """Verify that an S3 URI is allowed and accessible."""
    _s3_parts(uri)
    if not config.pipeline_submission_s3_allowed_prefixes:
        raise InvalidPipeline("No permitted S3 input scope is configured.")
    if not _within_s3_scope(uri, config.pipeline_submission_s3_allowed_prefixes):
        raise InvalidPipeline(f"S3 input is outside the permitted scope: {uri}")
    bucket, key = _s3_parts(uri)
    try:
        boto3.client("s3").head_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as error:
        raise InvalidPipeline(f"S3 input is not accessible: {uri}") from error
    return uri


def _safe_filename(filename: str) -> str:
    """Validate an upload filename."""
    if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename or "\0" in filename:
        raise InvalidPipeline("Upload filename must be a single file name.")
    return filename


def _safe_component(value: str) -> str:
    """Convert a value into a safe path component."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _upload_max_bytes(config) -> int:
    """Return the configured upload size limit in bytes."""
    return config.local_file_provider_upload_max_file_size_mb * 1024 * 1024


def _jwt_payload(config, **values) -> str:
    """Create a signed upload token."""
    payload = {
        **values,
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=config.pipeline_submission_upload_expires_in_sec)).timestamp()),
    }
    return jwt.encode(
        payload,
        config.local_file_provider_jwt_secret_key,
        algorithm=config.local_file_provider_jwt_algorithm,
    )


def _allocate_upload(config, name: str, input_name: str, destination: str, filename: str,
                     expected_size: int | None = None) -> SubmissionUpload:
    """Sign an upload to an already allocated destination."""
    expires = config.pipeline_submission_upload_expires_in_sec
    max_bytes = _upload_max_bytes(config)
    payload = dict(kind="pipeline-submission-upload", pipeline=name, input=input_name)
    if expected_size is not None:
        payload["expected_size"] = expected_size
    if destination.startswith("s3://"):
        _s3_parts(destination)
        if len(_s3_parts(destination)[1].encode()) > 1024:
            raise InvalidPipeline("Upload path exceeds the S3 key length limit.")
        token = _jwt_payload(config, **payload, s3_uri=destination)
        options = {"min_bytes": 0} if expected_size is not None else {}
        signed = S3Provider.presigned_post(destination, expires, max_bytes=max_bytes, **options)
        if signed is None:
            raise InvalidPipeline("Unable to allocate an S3 upload.")
    else:
        path = Path(destination).resolve()
        roots = [Path(item).resolve() for item in config.local_file_provider_upload_allowed_roots]
        if not any(path.is_relative_to(root) for root in roots):
            raise InvalidPipeline("Pipeline upload root is not an allowed local upload root.")
        token = _jwt_payload(config, **payload, filepath=str(path))
        signed = SignedUrl(
            url=f"{config.local_file_provider_server_url}/upload?{urlencode({'token': token})}",
            file=filename,
            fields=[SignedUrlField(name="token", value=token)],
        )
    return SubmissionUpload(
        upload_id=token, url=signed.url, file=signed.file, fields=signed.fields,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires), max_bytes=max_bytes,
    )


def create_submission_upload(services, name: str, input_name: str, filename: str, slices=None) -> SubmissionUpload:
    """Allocate an upload destination and signed upload details."""
    dataset = next((item for item in build_submission_form(services, name, slices).inputs if item.name == input_name), None)
    if dataset is None or not dataset.supported or SubmissionInputMethod.UPLOAD not in dataset.methods:
        raise InvalidPipeline(f"Uploads are not supported for input {input_name}.")
    if dataset.kind is SubmissionDatasetKind.PARTITIONED:
        raise InvalidPipeline("Partitioned inputs require a folder upload.")
    filename = _safe_filename(filename)
    root = _upload_root(services.config, name).rstrip("/")
    destination = f"{root}/{uuid4()}/inputs/{_safe_component(input_name)}/{filename}"
    return _allocate_upload(services.config, name, input_name, destination, filename)


def _folder_manifest(config, files: list[SubmissionFolderFileInput]) -> list[dict[str, Any]]:
    """Validate browser paths and sizes before allocating any destinations."""
    if not files or len(files) > config.pipeline_submission_partition_upload_max_files:
        raise InvalidPipeline(f"A folder must contain 1 to {config.pipeline_submission_partition_upload_max_files} files.")
    result = []
    seen = set()
    for file in files:
        path = file.relative_path
        parts = path.split("/")
        if (any(part in {"", ".", ".."} or len(part.encode()) > 255 for part in parts)
                or "\\" in path or ":" in path or any(ord(char) < 32 for char in path)
                or len(path.encode()) > 1024):
            raise InvalidPipeline("Folder files must have safe relative paths without traversal.")
        if path in seen:
            raise InvalidPipeline(f"Folder contains duplicate path: {path}")
        if (not math.isfinite(file.size) or file.size < 0 or not float(file.size).is_integer()
                or file.size > _upload_max_bytes(config)):
            raise InvalidPipeline(f"Invalid size or per-file limit exceeded: {path}")
        seen.add(path)
        result.append({"path": path, "size": int(file.size)})
    if sum(file["size"] for file in result) > config.pipeline_submission_partition_upload_max_size_mb * 1024 * 1024:
        raise InvalidPipeline("Folder exceeds the total upload size limit.")
    return result


def create_submission_folder_upload(services, name: str, input_name: str,
                                    files: list[SubmissionFolderFileInput], slices=None) -> SubmissionFolderUpload:
    """Allocate one directory and bind its complete manifest to a signed token."""
    dataset = next((item for item in build_submission_form(services, name, slices).inputs if item.name == input_name), None)
    if (dataset is None or not dataset.supported or dataset.kind is not SubmissionDatasetKind.PARTITIONED
            or SubmissionInputMethod.UPLOAD not in dataset.methods):
        raise InvalidPipeline(f"Folder uploads are not supported for input {input_name}.")
    config = services.config
    manifest = _folder_manifest(config, files)
    if not any(file["path"].endswith(dataset.filename_suffix or "") for file in manifest):
        raise InvalidPipeline(f"Folder must contain at least one file ending in {dataset.filename_suffix!r}.")
    root = _upload_root(config, name).rstrip("/")
    destination = f"{root}/{uuid4()}/inputs/{_safe_component(input_name)}"
    if not root.startswith("s3://"):
        destination = str(Path(destination).resolve())
    uploads = [SubmissionFolderFileUpload(
        relative_path=file["path"],
        upload=_allocate_upload(config, name, input_name, f"{destination}/{file['path']}",
                                file["path"].rsplit("/", 1)[-1], file["size"]),
    ) for file in manifest]
    token = _jwt_payload(config, kind="pipeline-submission-folder-upload", pipeline=name,
                         input=input_name, destination=destination, files=manifest)
    return SubmissionFolderUpload(upload_id=token, files=uploads)


def _uploaded_file_size(config, location: str, root: str) -> int:
    """Verify storage scope and return the actual size of an uploaded file."""
    if location.startswith("s3://"):
        if not root.startswith("s3://") or not _within_s3_scope(location, [root]):
            raise InvalidPipeline("Upload destination is outside the configured upload root.")
        bucket, key = _s3_parts(location)
        try:
            return boto3.client("s3").head_object(Bucket=bucket, Key=key)["ContentLength"]
        except (ClientError, BotoCoreError) as error:
            raise InvalidPipeline("Uploaded S3 object does not exist or is inaccessible.") from error
    path = Path(location).resolve()
    roots = [Path(item).resolve() for item in config.local_file_provider_upload_allowed_roots]
    if root.startswith("s3://") or not path.is_relative_to(Path(root).resolve()):
        raise InvalidPipeline("Upload destination is outside the configured upload root.")
    if not any(path.is_relative_to(allowed) for allowed in roots):
        raise InvalidPipeline("Upload destination is outside the configured local root.")
    try:
        if not path.is_file():
            raise InvalidPipeline("Uploaded file does not exist.")
        return path.stat().st_size
    except OSError as error:
        raise InvalidPipeline("Uploaded file is inaccessible.") from error


def _decode_upload(services, submission: PipelineSubmissionInput, source: SubmissionDatasetInput,
                   partitioned: bool = False) -> str:
    """Validate a file or complete folder token and resolve its location."""
    if not source.upload_id:
        raise InvalidPipeline("An upload ID is required.")
    config = services.config
    try:
        payload = jwt.decode(source.upload_id, config.local_file_provider_jwt_secret_key,
                             algorithms=[config.local_file_provider_jwt_algorithm])
    except jwt.InvalidTokenError as error:
        raise InvalidPipeline("Upload ID is invalid or expired.") from error
    kind = "pipeline-submission-folder-upload" if partitioned else "pipeline-submission-upload"
    if payload.get("kind") != kind or payload.get("pipeline") != submission.name or payload.get("input") != source.name:
        raise InvalidPipeline("Upload ID does not belong to this pipeline input or upload type.")
    root = _upload_root(config, submission.name)
    if partitioned:
        destination = payload["destination"]
        manifest = _folder_manifest(config, [SubmissionFolderFileInput(relative_path=file["path"], size=file["size"])
                                             for file in payload["files"]])
        sizes = None
        if destination.startswith("s3://"):
            if not root.startswith("s3://") or not _within_s3_scope(destination, [root]):
                raise InvalidPipeline("Upload destination is outside the configured upload root.")
            bucket, key = _s3_parts(destination)
            prefix = key.rstrip("/") + "/"
            try:
                pages = boto3.client("s3").get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
                sizes = {item["Key"]: item["Size"] for page in pages for item in page.get("Contents", [])}
            except (ClientError, BotoCoreError) as error:
                raise InvalidPipeline("Uploaded S3 folder is inaccessible.") from error
        for file in manifest:
            size = (sizes.get(prefix + file["path"]) if sizes is not None
                    else _uploaded_file_size(config, f"{destination}/{file['path']}", root))
            if size is None:
                raise InvalidPipeline(f"Uploaded folder file does not exist: {file['path']}")
            if size != file["size"]:
                raise InvalidPipeline(f"Uploaded folder file has the wrong size: {file['path']}")
        return destination.rstrip("/") + "/"
    location = payload.get("s3_uri") or payload.get("filepath")
    if not location:
        raise InvalidPipeline("Upload ID has no destination.")
    if _uploaded_file_size(config, location, root) > _upload_max_bytes(config):
        raise InvalidPipeline("Uploaded file exceeds the maximum size.")
    return location


def _check_partitioned_location(name: str, config: Mapping[str, Any], location: str) -> str:
    """Use Kedro's suffix and checkpoint rules without loading or confirming partitions."""
    try:
        dataset = AbstractDataset.from_config(name, _replace_location(config, location))
        # exists() cannot distinguish a directory marker from a partition when the suffix is empty.
        eligible = dataset._list_partitions()
        if "version" in dataset._dataset_config:
            eligible = [path for partition in eligible for path in dataset._filesystem.find(partition, **dataset._load_args)
                        if path.endswith(dataset._filename_suffix)]
        if not any(not path.endswith("/") and dataset._filesystem.isfile(path) for path in eligible):
            raise InvalidPipeline("No usable partitions were found matching the configured suffix and checkpoint.")
    except (DatasetError, OSError, BotoCoreError) as error:
        raise InvalidPipeline("Partition discovery failed; check storage access and dataset configuration.") from error
    return location


def _check_s3_prefix(server_config, uri: str) -> str:
    """Normalize a directory prefix and guard its S3 scope before discovery."""
    parsed = urlparse(uri)
    if (parsed.scheme != "s3" or not parsed.netloc or parsed.query or parsed.fragment
            or "@" in parsed.netloc or ":" in parsed.netloc):
        raise InvalidPipeline("S3 prefixes must be s3://bucket/prefix URIs.")
    location = uri.rstrip("/") + "/"
    if not _within_s3_scope(location, server_config.pipeline_submission_s3_allowed_prefixes):
        raise InvalidPipeline("S3 prefix is outside the permitted scope.")
    return location


def _replace_location(config: Mapping[str, Any], location: str | list[str]) -> dict[str, Any]:
    """Replace a catalog dataset location."""
    result = copy.deepcopy(dict(config))
    key = _dataset_location_key(result)
    if key is None:
        raise InvalidPipeline("Input dataset has no server-configured file location.")
    result[key] = location
    return result


def _derive_input_uri(uri: str, rule: SubmissionInputDerivation) -> str:
    """Resolve a configured suffix operation or Python regex substitution."""
    if rule.append_suffix is not None:
        return uri + rule.append_suffix
    if rule.regex_sub is not None:
        return re.sub(rule.regex_sub.pattern, rule.regex_sub.replacement, uri)
    replacement = rule.replace_suffix
    if replacement is None or not uri.endswith(replacement.from_suffix):
        suffix = replacement.from_suffix if replacement else ""
        raise InvalidPipeline(f"Source URI must end with {suffix!r} for suffix replacement.")
    _s3_parts(uri)
    return uri[:-len(replacement.from_suffix)] + replacement.to_suffix


def _prepare_submission(services, submission: PipelineSubmissionInput):
    """Validate and materialize a pipeline submission request."""
    selected, catalog, resolved_catalog, defaults = _form_context(
        services, submission.name, submission.slices
    )
    form = build_submission_form(services, submission.name, submission.slices)
    input_specs = {item.name: item for item in form.inputs}
    errors: list[SubmissionValidationError] = []
    sources: dict[str, SubmissionDatasetInput] = {}
    for source in submission.inputs:
        if source.name in sources:
            errors.append(SubmissionValidationError(path=source.name, message="Input was supplied more than once."))
        sources[source.name] = source
    resolved_inputs = []
    failed_derivations = set()
    for registration in services.config.dataset_input_derivations:
        if registration.pipeline_name != submission.name:
            continue
        target = registration.dataset_name
        descriptor = input_specs.get(target)
        if descriptor is None:
            continue
        rule = descriptor.derivation
        source = sources.get(rule.source_dataset) if rule else None
        if target in sources or not rule or source is None or source.method is not SubmissionInputMethod.S3_URI:
            continue
        try:
            uri = _derive_input_uri(source.s3_uri, rule) if source.s3_uri else None
        except InvalidPipeline as error:
            errors.append(SubmissionValidationError(path=target, message=str(error)))
            sources.pop(target, None)
            failed_derivations.add(target)
            continue
        sources[target] = SubmissionDatasetInput(name=target, method=SubmissionInputMethod.S3_URI, s3_uri=uri)
        if uri:
            resolved_inputs.append(ResolvedSubmissionInput(name=target, s3_uri=uri))
    expected = set(input_specs) - failed_derivations
    for name in sorted(expected - set(sources)):
        errors.append(SubmissionValidationError(path=name, message="Required input was not supplied."))
    for name in sorted(set(sources) - expected):
        errors.append(SubmissionValidationError(path=name, message="Input is not free in the selected graph."))

    merged_parameters = copy.deepcopy(dict(defaults))
    specs = _parameter_specs(selected, defaults)
    seen_parameters: set[tuple[str, ...]] = set()
    for override in submission.parameters:
        segments = tuple(override.segments)
        spec = specs.get(segments)
        path = ".".join(segments)
        if segments in seen_parameters:
            errors.append(SubmissionValidationError(path=path, message="Parameter was supplied more than once."))
            continue
        seen_parameters.add(segments)
        if spec is None:
            errors.append(SubmissionValidationError(path=path, message="Parameter path is not editable in this graph."))
            continue
        if not spec.editable:
            errors.append(SubmissionValidationError(path=path, message=spec.reason or "Parameter is read-only."))
            continue
        if spec.value_type is not override.type:
            errors.append(SubmissionValidationError(path=path, message=f"Expected parameter type {spec.value_type.value}."))
            continue
        if not _validate_parameter_value(override.value, override.type):
            errors.append(SubmissionValidationError(path=path, message="Parameter value does not match its declared type."))
            continue
        try:
            value = float(override.value) if spec.value_type is SubmissionValueType.FLOAT else override.value
            _set_parameter(merged_parameters, segments, value)
        except (InvalidPipeline, OverflowError) as error:
            errors.append(SubmissionValidationError(path=path, message=str(error)))

    catalog_inputs: list[DataSetInput] = []
    for name, source in sources.items():
        descriptor = input_specs.get(name)
        if descriptor is None or not descriptor.supported:
            if descriptor is not None:
                errors.append(SubmissionValidationError(path=name, message=descriptor.reason or "Input is not supported."))
            continue
        if source.method not in descriptor.methods:
            errors.append(SubmissionValidationError(path=name, message="Input method is not supported."))
            continue
        try:
            if source.method is SubmissionInputMethod.S3_URI:
                if descriptor.kind is SubmissionDatasetKind.COLLECTION:
                    if source.s3_uri or not source.s3_uris:
                        raise InvalidPipeline("Supply a nonempty S3 URI list for this collection input.")
                    if len(set(source.s3_uris)) != len(source.s3_uris):
                        raise InvalidPipeline("Collection input contains duplicate S3 URIs.")
                    location = [_check_s3_uri(services.config, uri) for uri in source.s3_uris]
                else:
                    if source.s3_uris or not source.s3_uri:
                        raise InvalidPipeline("Supply one S3 URI for this input.")
                    context = DatasetInputContext(submission.name, name, resolved_catalog.get(name) or catalog.get(name) or {}, tuple(submission.slices or []), None)
                    provider = find_input_provider(services, context, [source.method.value])
                    uri = provider.resolve(context, source.s3_uri) if provider else source.s3_uri
                    location = (_check_s3_prefix(services.config, uri)
                                if descriptor.kind is SubmissionDatasetKind.PARTITIONED
                                else _check_s3_uri(services.config, uri))
            else:
                location = _decode_upload(services, submission, source,
                                          partitioned=descriptor.kind is SubmissionDatasetKind.PARTITIONED)
            original = resolved_catalog.get(name) or catalog.get(name)
            if descriptor.kind is SubmissionDatasetKind.PARTITIONED:
                location = _check_partitioned_location(name, original, location)
            catalog_inputs.append(DataSetInput(name=name, config=json.dumps(_replace_location(original, location))))
        except InvalidPipeline as error:
            errors.append(SubmissionValidationError(path=name, message=str(error)))

    if errors:
        return None, errors, [], resolved_inputs

    managed_outputs = [
        output.name
        for output in form.outputs
        if output.managed
    ]
    pipeline_input = PipelineInput(
        name=submission.name,
        state=PipelineInputStatus.READY,
        parameters=_parameter_inputs(merged_parameters),
        data_catalog=catalog_inputs,
        slices=list(submission.slices),
    )
    transform = services.config.pipeline_submission_transforms.get(submission.name)
    if transform:
        module, name = transform.rsplit(".", 1)
        try:
            pipeline_input, managed_outputs = getattr(import_module(module), name)(
                pipeline_input, merged_parameters, managed_outputs
            )
        except (InvalidPipeline, ValueError) as error:
            return None, [SubmissionValidationError(path=None, message=str(error))], [], resolved_inputs
    return pipeline_input, [], managed_outputs, resolved_inputs


async def validate_pipeline_submission(services, submission: PipelineSubmissionInput) -> SubmissionValidationResult:
    """Validate a submission without persisting or running it."""
    try:
        pipeline_input, errors, managed_outputs, resolved_inputs = _prepare_submission(services, submission)
    except (InvalidPipeline, ValueError) as error:
        return SubmissionValidationResult(
            valid=False,
            errors=[SubmissionValidationError(path=None, message=str(error))],
        )
    if errors:
        return SubmissionValidationResult(valid=False, errors=errors, resolved_inputs=resolved_inputs)
    try:
        from .pipeline_service import create_pipeline

        await create_pipeline(
            services,
            pipeline_input,
            None,
            unique_paths=managed_outputs,
            dry_run=True,
        )
    except (InvalidPipeline, ValueError) as error:
        return SubmissionValidationResult(
            valid=False,
            errors=[SubmissionValidationError(path=None, message=str(error))],
            resolved_inputs=resolved_inputs,
        )
    return SubmissionValidationResult(valid=True, errors=[], resolved_inputs=resolved_inputs)


async def submit_pipeline(services, submission: PipelineSubmissionInput, caller) -> Any:
    """Create and start a validated pipeline submission."""
    pipeline_input, errors, managed_outputs, _ = _prepare_submission(services, submission)
    if errors:
        raise InvalidPipeline("; ".join(error.message for error in errors))
    from .pipeline_service import create_pipeline

    return await create_pipeline(
        services,
        pipeline_input,
        caller,
        unique_paths=managed_outputs,
    )
