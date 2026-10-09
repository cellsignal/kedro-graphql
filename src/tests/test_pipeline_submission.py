from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import json

import jwt
import pytest
from kedro.pipeline import Pipeline, node

from kedro_graphql import pipeline_submission
from kedro_graphql.config import load_config
from kedro_graphql.models import PipelineSlice, PipelineSliceType
from kedro_graphql.exceptions import InvalidPipeline
from kedro_graphql.pipeline_submission import (
    PipelineSubmissionInput,
    SubmissionDatasetInput,
    SubmissionInputMethod,
    SubmissionParameterInput,
    SubmissionValueType,
    _check_s3_uri,
    _decode_upload,
    build_submission_form,
    create_submission_upload,
    _prepare_submission,
    _parameter_visible,
    validate_pipeline_submission,
)


def _services(tmp_path, monkeypatch):
    def transform(raw, amount, values, objects, enabled, nullable):
        return raw

    pipeline = Pipeline(
        [
            node(
                transform,
                [
                    "raw",
                    "params:settings.amount",
                    "params:settings.values",
                    "params:settings.objects",
                    "params:enabled",
                    "params:nullable",
                ],
                "out",
                name="transform",
            )
        ]
    )
    aggregate_pipeline = Pipeline(
        [
            node(
                lambda raw, settings: raw,
                ["raw", "params:settings"],
                "out",
                name="aggregate",
            )
        ]
    )
    catalog = {
        "raw": {"type": "text.TextDataset", "filepath": "/tmp/raw.txt"},
        "out": {"type": "text.TextDataset", "filepath": "/tmp/out.txt"},
    }
    parameters = {
        "settings": {
            "amount": 3,
            "values": [1, "two", None],
            "objects": [{"value": 1}],
        },
        "enabled": False,
        "nullable": None,
    }
    monkeypatch.setattr(
        "kedro_graphql.pipeline_submission.load_pipeline_configuration",
        lambda *args: (catalog, parameters),
    )
    config = load_config(
        {
            "pipeline_submission_s3_allowed_prefixes": ["s3://allowed/input"],
            "local_file_provider_upload_allowed_roots": [str(tmp_path)],
            "pipeline_submission_upload_root": str(tmp_path / "submissions"),
        }
    )
    return SimpleNamespace(
        input_providers=(),
        metadata=SimpleNamespace(pipelines={"toy": pipeline, "aggregate": aggregate_pipeline}),
        config=config,
    )


def test_form_applies_slices_and_describes_typed_parameter_leaves(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)

    form = build_submission_form(services, "toy")

    assert [item.name for item in form.inputs] == ["raw"]
    assert [item.name for item in form.outputs] == ["out"]
    assert form.inputs[0].methods == [SubmissionInputMethod.S3_URI, SubmissionInputMethod.UPLOAD]
    rows = {row.path: row for row in form.parameters}
    assert rows["settings.amount"].type is SubmissionValueType.INTEGER
    assert rows["settings.amount"].segments == ["settings", "amount"]
    assert rows["settings.values"].editable
    assert rows["settings.values"].default_value == [1, "two", None]
    assert not rows["settings.objects"].editable
    assert rows["enabled"].default_value is False
    assert rows["nullable"].type is SubmissionValueType.NULL

    aggregate = build_submission_form(services, "aggregate")
    aggregate_rows = {row.path: row for row in aggregate.parameters}
    assert aggregate_rows["settings.amount"].editable
    assert aggregate_rows["settings.values"].editable

    sliced = build_submission_form(
        services,
        "toy",
        [PipelineSlice(slice=PipelineSliceType.NODE_NAMES, args=["transform"])],
    )
    assert [item.name for item in sliced.inputs] == ["raw"]


@pytest.mark.parametrize(("path", "allowlist", "disallowlist", "visible"), [
    ("settings.amount", None, [], True),
    ("settings.amount", [], [], False),
    ("settings.amount", None, ["settings"], False),
    ("settings.amount", ["settings"], [], True),
    ("enabled", ["settings"], [], False),
    ("settings.amount", ["settings"], ["settings.amount"], False),
    ("settings.amount", ["settings.amount"], ["settings"], True),
    ("settings.amount", ["settings.amount"], ["settings.amount"], False),
    ("settings.amount", ["settings"], ["settings"], False),
    ("settings.deep.amount", ["settings", "settings.deep.amount"], ["settings.deep"], True),
    ("settings.deep.amount", ["settings.deep.amount", "settings"], ["settings.deep"], True),
    ("settings.deep.amount", ["settings.deep"], ["settings", "settings.deep.amount"], False),
    ("settings.deep.amount", ["settings.deep"], ["settings.deep.amount", "settings"], False),
    ("settings_extra.amount", None, ["settings"], True),
    ("settings_extra.amount", ["settings"], [], False),
])
def test_parameter_visibility_uses_specificity(path, allowlist, disallowlist, visible):
    assert _parameter_visible(path, allowlist, disallowlist) is visible


def test_form_visibility_is_per_pipeline_and_retains_all_metadata(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    services.config.pipeline_submission_parameter_allowlists = {"toy": ["settings"]}
    services.config.pipeline_submission_parameter_disallowlists = {"toy": ["settings.objects"]}
    rows = build_submission_form(services, "toy").parameters
    assert len(rows) == 5
    assert [row.path for row in rows if row.visible_in_form] == [
        "settings.amount", "settings.values",
    ]
    assert all(row.visible_in_form for row in build_submission_form(services, "aggregate").parameters)
    services.config.pipeline_submission_parameter_allowlists["toy"] = []
    assert not any(row.visible_in_form for row in build_submission_form(services, "toy").parameters)


@pytest.mark.parametrize("override", [False, True])
def test_hidden_parameters_keep_defaults_and_accept_api_overrides(tmp_path, monkeypatch, override):
    services = _services(tmp_path, monkeypatch)
    services.config.pipeline_submission_parameter_disallowlists = {"toy": ["settings.amount"]}
    monkeypatch.setattr("kedro_graphql.pipeline_submission._check_s3_uri", lambda config, uri: uri)
    submission = PipelineSubmissionInput(
        name="toy",
        inputs=[SubmissionDatasetInput(
            name="raw", method=SubmissionInputMethod.S3_URI, s3_uri="s3://allowed/input/raw.txt",
        )],
        parameters=[SubmissionParameterInput(
            segments=["settings", "amount"], type=SubmissionValueType.INTEGER, value=9,
        )] if override else [],
    )
    hidden = next(row for row in build_submission_form(services, "toy").parameters if row.path == "settings.amount")
    assert not hidden.visible_in_form
    assert hidden.default_value == 3
    assert hidden.editable
    pipeline_input, errors, _, _ = _prepare_submission(services, submission)
    assert not errors
    settings = next(item for item in pipeline_input.parameters if item.name == "settings")
    assert json.loads(settings.value) == {
        "amount": 9 if override else 3,
        "values": [1, "two", None],
        "objects": [{"value": 1}],
    }


@pytest.mark.parametrize("default", [None, False, 0, [], {}])
def test_hidden_falsey_defaults_are_valid(tmp_path, monkeypatch, default):
    services = _services(tmp_path, monkeypatch)
    _, parameters = pipeline_submission.load_pipeline_configuration()
    parameters["enabled"] = default
    services.config.pipeline_submission_parameter_disallowlists = {"toy": ["enabled"]}
    hidden = next(row for row in build_submission_form(services, "toy").parameters if row.path == "enabled")
    assert not hidden.visible_in_form
    assert hidden.default_value == default


@pytest.mark.parametrize("path", ["enabled", "settings.amount"])
def test_hidden_required_parameter_without_default_rejects_form(tmp_path, monkeypatch, path):
    services = _services(tmp_path, monkeypatch)
    _, parameters = pipeline_submission.load_pipeline_configuration()
    if path == "enabled":
        del parameters["enabled"]
    else:
        del parameters["settings"]["amount"]
    assert path in {row.path for row in build_submission_form(services, "toy").parameters}
    services.config.pipeline_submission_parameter_disallowlists = {"toy": [path]}
    with pytest.raises(InvalidPipeline, match="Hidden parameter") as error:
        build_submission_form(services, "toy")
    assert str(error.value) == f"Hidden parameter {path!r} for pipeline 'toy' has no server default."


@pytest.mark.parametrize(("value", "valid"), [(1, True), (1.5, True), (True, False), (float("inf"), False), (10**400, False)])
def test_float_overrides_accept_json_integers_and_preserve_float_type(tmp_path, monkeypatch, value, valid):
    services = _services(tmp_path, monkeypatch)
    _, defaults = pipeline_submission.load_pipeline_configuration()
    defaults["settings"]["amount"] = 3.5
    monkeypatch.setattr("kedro_graphql.pipeline_submission._check_s3_uri", lambda config, uri: uri)
    submission = PipelineSubmissionInput(
        name="toy",
        inputs=[SubmissionDatasetInput(name="raw", method=SubmissionInputMethod.S3_URI, s3_uri="s3://allowed/input/raw.txt")],
        parameters=[SubmissionParameterInput(segments=["settings", "amount"], type=SubmissionValueType.FLOAT, value=value)],
    )
    prepared, errors, _, _ = _prepare_submission(services, submission)
    if not valid:
        assert errors[0].path == "settings.amount"
        return
    assert not errors
    settings = next(item for item in prepared.parameters if item.name == "settings")
    result = json.loads(settings.value)["amount"]
    assert result == value
    assert type(result) is float


def test_direct_s3_uri_is_scoped_and_head_checked(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    client = Mock()
    monkeypatch.setattr("kedro_graphql.pipeline_submission.boto3.client", lambda name: client)

    assert _check_s3_uri(services.config, "s3://allowed/input/file.csv") == "s3://allowed/input/file.csv"
    client.head_object.assert_called_once_with(Bucket="allowed", Key="input/file.csv")

    with pytest.raises(Exception, match="outside the permitted scope"):
        _check_s3_uri(services.config, "s3://allowed/other/file.csv")


def test_form_advertises_only_configured_input_methods(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    services.config = services.config.model_copy(
        update={"pipeline_submission_s3_allowed_prefixes": []}
    )
    assert build_submission_form(services, "toy").inputs[0].methods == [
        SubmissionInputMethod.UPLOAD
    ]

    services.config = services.config.model_copy(
        update={"pipeline_submission_upload_root": "/outside/allowed/root"}
    )
    descriptor = build_submission_form(services, "toy").inputs[0]
    assert descriptor.methods == []
    assert not descriptor.supported


def test_local_upload_is_server_allocated_and_checked(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    upload = create_submission_upload(services, "toy", "raw", "input.txt")

    payload = jwt.decode(
        upload.upload_id,
        services.config.local_file_provider_jwt_secret_key,
        algorithms=[services.config.local_file_provider_jwt_algorithm],
    )
    path = tmp_path / "submissions" / payload["filepath"].split("/submissions/", 1)[1]
    path.parent.mkdir(parents=True)
    path.write_text("input")
    submission = PipelineSubmissionInput(
        name="toy",
        inputs=[
            SubmissionDatasetInput(
                name="raw",
                method=SubmissionInputMethod.UPLOAD,
                upload_id=upload.upload_id,
            )
        ],
    )

    assert _decode_upload(services, submission, submission.inputs[0]) == str(path.resolve())


def test_prepare_submission_preserves_typed_overrides_and_rejects_complex_arrays(
    tmp_path, monkeypatch
):
    services = _services(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "kedro_graphql.pipeline_submission._check_s3_uri",
        lambda config, uri: uri,
    )
    submission = PipelineSubmissionInput(
        name="toy",
        parameters=[
            SubmissionParameterInput(
                segments=["settings", "values"],
                type=SubmissionValueType.ARRAY,
                value=[False, 2.5],
            )
        ],
        inputs=[
            SubmissionDatasetInput(
                name="raw",
                method=SubmissionInputMethod.S3_URI,
                s3_uri="s3://allowed/input/raw.txt",
            )
        ],
    )

    pipeline_input, errors, outputs, _ = _prepare_submission(services, submission)

    assert not errors
    assert outputs == ["out"]
    settings = next(parameter for parameter in pipeline_input.parameters if parameter.name == "settings")
    assert json.loads(settings.value)["values"] == [False, 2.5]
    assert json.loads(pipeline_input.data_catalog[0].config)["filepath"] == "s3://allowed/input/raw.txt"

    submission.parameters[0].value = [{"not": "a leaf"}]
    _, errors, _, _ = _prepare_submission(services, submission)
    assert errors[0].path == "settings.values"


@pytest.mark.asyncio
async def test_validation_recomputes_the_graph_before_accepting_submission(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "kedro_graphql.pipeline_submission._check_s3_uri",
        lambda config, uri: uri,
    )
    submission = PipelineSubmissionInput(
        name="toy",
        inputs=[
            SubmissionDatasetInput(
                name="raw",
                method=SubmissionInputMethod.S3_URI,
                s3_uri="s3://allowed/input/raw.txt",
            )
        ],
    )
    dry_run = AsyncMock()
    with patch("kedro_graphql.pipeline_service.create_pipeline", dry_run):
        result = await validate_pipeline_submission(services, submission)

    assert result.valid
    dry_run.assert_awaited_once()
    assert dry_run.await_args.kwargs["unique_paths"] == ["out"]
    assert dry_run.await_args.kwargs["dry_run"] is True


def test_submission_schema_contains_new_operations():
    from kedro_graphql.decorators import TYPE_PLUGINS
    from kedro_graphql.schema import build_schema

    schema = build_schema(TYPE_PLUGINS)
    rendered = str(schema)
    assert "pipelineSubmissionForm" in rendered
    assert "visibleInForm: Boolean!" in rendered
    assert "createPipelineSubmissionFolderUpload" in rendered
    assert "derivation: SubmissionInputDerivation" in rendered
    assert "regexSub: SubmissionRegexSubstitution" in rendered
    assert "resolvedInputs: [ResolvedSubmissionInput!]!" in rendered
    assert "filenameSuffix: String" in rendered
    assert "folderUploadLimits: SubmissionFolderUploadLimits" in rendered
    assert "submitPipeline" in rendered
    assert "pipelineSubmissionChoices" not in rendered


def test_form_reports_effective_server_runner(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    assert build_submission_form(services, "toy").runner == "kedro.runner.SequentialRunner"
    services.config.pipeline_runners = {"toy": "ab_discovery.runners.argo.ArgoRunner"}
    assert build_submission_form(services, "toy").runner == "ab_discovery.runners.argo.ArgoRunner"


def test_pipeline_upload_root_override_is_used(tmp_path, monkeypatch):
    from kedro_graphql.pipeline_submission import _upload_root
    services = _services(tmp_path, monkeypatch)
    services.config.pipeline_submission_upload_roots = {"toy": "s3://allowed/input/toy"}
    assert _upload_root(services.config, "toy") == "s3://allowed/input/toy"
    assert _upload_root(services.config, "aggregate") == services.config.pipeline_submission_upload_root
    assert SubmissionInputMethod.UPLOAD in build_submission_form(services, "toy").inputs[0].methods


def test_s3_upload_uses_pipeline_root_and_rejects_changed_root(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    services = _services(tmp_path, monkeypatch)
    services.config.pipeline_submission_upload_roots = {"toy": "s3://allowed/input/toy"}
    sign = Mock(return_value=SimpleNamespace(url="https://s3.example", file="input.txt", fields=[]))
    monkeypatch.setattr("kedro_graphql.pipeline_submission.S3Provider.presigned_post", sign)
    upload = create_submission_upload(services, "toy", "raw", "input.txt")
    assert sign.call_args.args[0].startswith("s3://allowed/input/toy/")
    head = Mock(return_value={"ContentLength": 3})
    monkeypatch.setattr("kedro_graphql.pipeline_submission.boto3.client", lambda *_args: SimpleNamespace(head_object=head))
    source = SubmissionDatasetInput(name="raw", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id)
    submission = PipelineSubmissionInput(name="toy", inputs=[source])
    assert _decode_upload(services, submission, source).startswith("s3://allowed/input/toy/")
    services.config.pipeline_submission_upload_roots["toy"] = "s3://allowed/input/other"
    with pytest.raises(InvalidPipeline, match="outside the configured upload root"):
        _decode_upload(services, submission, source)


def test_local_upload_cannot_be_used_after_pipeline_switches_to_s3(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    upload = create_submission_upload(services, "toy", "raw", "input.txt")
    source = SubmissionDatasetInput(name="raw", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id)
    services.config.pipeline_submission_upload_roots = {"toy": "s3://allowed/input/toy"}
    with pytest.raises(InvalidPipeline, match="outside the configured upload root"):
        _decode_upload(services, PipelineSubmissionInput(name="toy", inputs=[source]), source)


def test_batch_limit_defaults_and_per_name_override(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    assert build_submission_form(services, "toy").max_batch_size == 10
    services.config.pipeline_submission_batch_max_sizes = {"toy": 3}
    assert build_submission_form(services, "toy").max_batch_size == 3
    assert build_submission_form(services, "aggregate").max_batch_size == 10


def test_submission_isolates_intermediate_outputs_and_keeps_shared_input(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    services.metadata.pipelines["toy"] = Pipeline([
        node(lambda raw: raw, "raw", "middle", name="first"),
        node(lambda middle: middle, "middle", "out", name="second"),
    ])
    catalog = {name: {"type": "text.TextDataset", "filepath": f"/tmp/{name}.txt"}
               for name in ("raw", "middle", "out")}
    monkeypatch.setattr("kedro_graphql.pipeline_submission.load_pipeline_configuration",
                        lambda *args: (catalog, {}))
    form = build_submission_form(services, "toy")
    assert [(output.name, output.free) for output in form.outputs] == [("middle", False), ("out", True)]
    assert [item.name for item in form.inputs] == ["raw"]
    monkeypatch.setattr("kedro_graphql.pipeline_submission._check_s3_uri", lambda config, uri: uri)
    submission = PipelineSubmissionInput(name="toy", inputs=[SubmissionDatasetInput(
        name="raw", method=SubmissionInputMethod.S3_URI, s3_uri="s3://allowed/input/shared.txt")])
    pipeline_input, errors, managed, _ = _prepare_submission(services, submission)
    assert not errors
    assert managed == ["middle", "out"]
    from kedro_graphql.models import DataSet, Pipeline as PipelineModel
    from kedro_graphql.utils import generate_unique_paths
    for pipeline_id in ("first", "second"):
        record = PipelineModel(id=pipeline_id, name="toy", data_catalog=[
            DataSet(name=name, config=json.dumps(config)) for name, config in catalog.items()])
        generate_unique_paths(record, managed)
        locations = record.to_kedro()["data_catalog"]
        assert locations["raw"]["filepath"] == "/tmp/raw.txt"
        assert locations["middle"]["filepath"] == f"/tmp/{pipeline_id}/middle.txt"
        assert locations["out"]["filepath"] == f"/tmp/{pipeline_id}/out.txt"


def test_batch_limits_reject_nonpositive_values():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        load_config({"pipeline_submission_batch_max_size": 0})
    with pytest.raises(ValidationError):
        load_config({"pipeline_submission_batch_max_sizes": {"toy": -1}})


def test_locationless_memory_outputs_allow_batch_but_persistent_outputs_do_not(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    catalog = {"raw": {"type": "text.TextDataset", "filepath": "/tmp/raw.txt"},
               "out": {"type": "MemoryDataset"}}
    monkeypatch.setattr("kedro_graphql.pipeline_submission.load_pipeline_configuration",
                        lambda *args: (catalog, {}))
    form = build_submission_form(services, "toy")
    assert form.max_batch_size == 10
    assert form.batch_limit_reason is None
    # Simulate a custom persistent dataset with no standard location, keeping
    # catalog resolution itself on Kedro's real implementation.
    monkeypatch.setattr("kedro_graphql.pipeline_submission.AbstractDataset",
                        SimpleNamespace(from_config=Mock(return_value=object())))
    form = build_submission_form(services, "toy")
    assert form.max_batch_size == 1
    assert "out" in form.batch_limit_reason


def _partition_services(tmp_path, monkeypatch, dataset_type="kedro_datasets.partitions.PartitionedDataset", **options):
    services = _services(tmp_path, monkeypatch)
    catalog, parameters = pipeline_submission.load_pipeline_configuration()
    catalog["raw"] = {
        "type": dataset_type, "path": str(tmp_path / "source"),
        "dataset": "text.TextDataset", "filename_suffix": ".txt", **options,
    }
    return services, catalog


@pytest.mark.parametrize("dataset_type", [
    "partitions.PartitionedDataset", "kedro_datasets.partitions.PartitionedDataset",
    "partitions.IncrementalDataset", "kedro_datasets.partitions.IncrementalDataset",
])
def test_partitioned_form_supports_both_methods_and_exposes_limits(tmp_path, monkeypatch, dataset_type):
    services, _ = _partition_services(tmp_path, monkeypatch, dataset_type)
    input = build_submission_form(services, "toy").inputs[0]
    assert input.supported
    assert input.kind is pipeline_submission.SubmissionDatasetKind.PARTITIONED
    assert input.methods == [SubmissionInputMethod.S3_URI, SubmissionInputMethod.UPLOAD]
    assert input.filename_suffix == ".txt"
    assert input.folder_upload_limits.max_files == 1000
    assert input.folder_upload_limits.max_total_bytes == 1024 ** 3
    with pytest.raises(InvalidPipeline, match="folder upload"):
        create_submission_upload(services, "toy", "raw", "file.txt")


def test_partition_detection_accepts_classes_and_subclasses():
    from kedro_datasets.partitions import PartitionedDataset

    class CustomPartitions(PartitionedDataset):
        pass

    assert pipeline_submission._dataset_kind({"type": CustomPartitions}) is pipeline_submission.SubmissionDatasetKind.PARTITIONED


@pytest.mark.parametrize("uri", ["s3://allowed/input/folder", "s3://allowed/input/folder/"])
def test_prefix_is_normalized_and_uses_kedro_discovery(tmp_path, monkeypatch, uri):
    services, catalog = _partition_services(tmp_path, monkeypatch)
    discovery = Mock(return_value="s3://allowed/input/folder/")
    monkeypatch.setattr(pipeline_submission, "_check_partitioned_location", discovery)
    head = Mock()
    monkeypatch.setattr(pipeline_submission.boto3, "client", head)
    submission = PipelineSubmissionInput(name="toy", inputs=[SubmissionDatasetInput(
        name="raw", method=SubmissionInputMethod.S3_URI, s3_uri=uri,
    )])
    result, errors, _, _ = _prepare_submission(services, submission)
    assert not errors
    assert json.loads(result.data_catalog[0].config)["path"] == "s3://allowed/input/folder/"
    discovery.assert_called_once_with("raw", catalog["raw"], "s3://allowed/input/folder/")
    head.assert_not_called()


@pytest.mark.parametrize("uri", ["s3://allowed/input-other/", "s3://other/input/", "https://allowed/input/", "s3://allowed/input/?secret=x"])
def test_prefix_scope_rejects_siblings_and_malformed_uris(tmp_path, monkeypatch, uri):
    services, _ = _partition_services(tmp_path, monkeypatch)
    with pytest.raises(InvalidPipeline):
        pipeline_submission._check_s3_prefix(services.config, uri)


def test_bucket_root_requires_explicit_scope(tmp_path, monkeypatch):
    services = _services(tmp_path, monkeypatch)
    with pytest.raises(InvalidPipeline):
        pipeline_submission._check_s3_prefix(services.config, "s3://allowed")
    services.config.pipeline_submission_s3_allowed_prefixes = ["s3://allowed/"]
    assert pipeline_submission._check_s3_prefix(services.config, "s3://allowed") == "s3://allowed/"


def test_discovery_requires_actual_suffix_matching_files(tmp_path):
    root = tmp_path / "nested"
    root.mkdir()
    config = {"type": "partitions.PartitionedDataset", "dataset": "text.TextDataset", "path": str(root), "filename_suffix": ".txt"}
    (root / "ignore.csv").write_text("ignored")
    with pytest.raises(InvalidPipeline, match="No usable partitions"):
        pipeline_submission._check_partitioned_location("raw", config, str(root))
    (root / "inner").mkdir()
    (root / "inner" / "good.txt").write_text("good")
    assert pipeline_submission._check_partitioned_location("raw", config, str(root)) == str(root)
    (root / "inner" / "good.txt").unlink()
    config["filename_suffix"] = ""
    assert pipeline_submission._check_partitioned_location("raw", config, str(root)) == str(root)
    (root / "ignore.csv").unlink()
    config["load_args"] = {"withdirs": True}
    with pytest.raises(InvalidPipeline, match="No usable partitions"):
        pipeline_submission._check_partitioned_location("raw", config, str(root))


def test_incremental_discovery_requires_eligible_partition_without_changing_checkpoint(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "001.txt").write_text("past")
    checkpoint = root / "CHECKPOINT"
    checkpoint.write_text("001")
    config = {"type": "partitions.IncrementalDataset", "dataset": "text.TextDataset", "path": str(root), "filename_suffix": ".txt"}
    with pytest.raises(InvalidPipeline, match="No usable partitions"):
        pipeline_submission._check_partitioned_location("raw", config, str(root))
    (root / "002.txt").write_text("new")
    assert pipeline_submission._check_partitioned_location("raw", config, str(root)) == str(root)
    assert checkpoint.read_text() == "001"


def test_directory_markers_and_inaccessible_storage_are_rejected(monkeypatch):
    from kedro.io import DatasetError
    dataset = Mock()
    dataset._dataset_config = {}
    dataset._list_partitions.return_value = ["bucket/prefix/"]
    monkeypatch.setattr(pipeline_submission.AbstractDataset, "from_config", Mock(return_value=dataset))
    with pytest.raises(InvalidPipeline, match="No usable partitions"):
        pipeline_submission._check_partitioned_location("raw", {"path": "s3://bucket/prefix/"}, "s3://bucket/prefix/")
    dataset._list_partitions.side_effect = DatasetError("access denied")
    with pytest.raises(InvalidPipeline, match="storage access"):
        pipeline_submission._check_partitioned_location("raw", {"path": "s3://bucket/prefix/"}, "s3://bucket/prefix/")


def _folder_files(*paths):
    return [pipeline_submission.SubmissionFolderFileInput(relative_path=path, size=3) for path in paths]


def _complete_local_folder(services, upload):
    for item in upload.files:
        payload = jwt.decode(item.upload.upload_id, services.config.local_file_provider_jwt_secret_key,
                             algorithms=[services.config.local_file_provider_jwt_algorithm])
        from pathlib import Path
        path = Path(payload["filepath"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"abc")


def test_folder_upload_preserves_subfolders_and_requires_complete_manifest(tmp_path, monkeypatch):
    services, _ = _partition_services(tmp_path, monkeypatch)
    upload = pipeline_submission.create_submission_folder_upload(services, "toy", "raw", _folder_files("a.txt", "nested/b.txt"))
    submission = PipelineSubmissionInput(name="toy", inputs=[SubmissionDatasetInput(name="raw", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id)])
    with pytest.raises(InvalidPipeline, match="does not exist"):
        _decode_upload(services, submission, submission.inputs[0], partitioned=True)
    _complete_local_folder(services, upload)
    location = _decode_upload(services, submission, submission.inputs[0], partitioned=True)
    from pathlib import Path
    assert (Path(location) / "nested/b.txt").read_bytes() == b"abc"
    result, errors, _, _ = _prepare_submission(services, submission)
    assert not errors
    assert json.loads(result.data_catalog[0].config)["path"] == location
    (Path(location) / "nested/b.txt").write_bytes(b"partial")
    with pytest.raises(InvalidPipeline, match="wrong size"):
        _decode_upload(services, submission, submission.inputs[0], partitioned=True)
    (Path(location) / "nested/b.txt").unlink()
    with pytest.raises(InvalidPipeline, match="does not exist"):
        _decode_upload(services, submission, submission.inputs[0], partitioned=True)


@pytest.mark.parametrize("path", ["../file.txt", "/file.txt", "a/../file.txt", "a//file.txt", "a\\file.txt", "C:/file.txt", "a/./file.txt", "a/\0.txt"])
def test_folder_paths_are_validated_before_signing(tmp_path, monkeypatch, path):
    services, _ = _partition_services(tmp_path, monkeypatch)
    with pytest.raises(InvalidPipeline, match="safe relative paths"):
        pipeline_submission.create_submission_folder_upload(services, "toy", "raw", _folder_files(path))


@pytest.mark.parametrize("files, message", [
    ([], "1 to"), (_folder_files("a.txt", "a.txt"), "duplicate"),
    (_folder_files("a.csv"), "at least one"),
    ([pipeline_submission.SubmissionFolderFileInput(relative_path="a.txt", size=-1)], "Invalid size"),
    ([pipeline_submission.SubmissionFolderFileInput(relative_path="a.txt", size=0.5)], "Invalid size"),
    ([pipeline_submission.SubmissionFolderFileInput(relative_path="a.txt", size=float("inf"))], "Invalid size"),
])
def test_folder_manifest_rejects_invalid_requests(tmp_path, monkeypatch, files, message):
    services, _ = _partition_services(tmp_path, monkeypatch)
    with pytest.raises(InvalidPipeline, match=message):
        pipeline_submission.create_submission_folder_upload(services, "toy", "raw", files)


def test_folder_limits_and_wrong_token_bindings(tmp_path, monkeypatch):
    services, _ = _partition_services(tmp_path, monkeypatch)
    services.config.pipeline_submission_partition_upload_max_files = 1
    with pytest.raises(InvalidPipeline, match="1 to 1"):
        pipeline_submission.create_submission_folder_upload(services, "toy", "raw", _folder_files("a.txt", "b.txt"))
    services.config.pipeline_submission_partition_upload_max_size_mb = 1
    oversized = [pipeline_submission.SubmissionFolderFileInput(relative_path="a.txt", size=1024**2 + 1)]
    with pytest.raises(InvalidPipeline, match="total upload"):
        pipeline_submission.create_submission_folder_upload(services, "toy", "raw", oversized)
    services.config.local_file_provider_upload_max_file_size_mb = 1
    with pytest.raises(InvalidPipeline, match="per-file"):
        pipeline_submission.create_submission_folder_upload(services, "toy", "raw", oversized)
    upload = pipeline_submission.create_submission_folder_upload(services, "toy", "raw", _folder_files("a.txt"))
    _complete_local_folder(services, upload)
    source = SubmissionDatasetInput(name="other", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id)
    with pytest.raises(InvalidPipeline, match="does not belong"):
        _decode_upload(services, PipelineSubmissionInput(name="toy"), source, partitioned=True)
    source.name = "raw"
    with pytest.raises(InvalidPipeline, match="upload type"):
        _decode_upload(services, PipelineSubmissionInput(name="toy"), source)
    services.config.pipeline_submission_upload_root = str(tmp_path / "different")
    with pytest.raises(InvalidPipeline, match="outside"):
        _decode_upload(services, PipelineSubmissionInput(name="toy"), source, partitioned=True)


def test_folder_s3_uploads_share_root_and_check_all_file_sizes(tmp_path, monkeypatch):
    services, _ = _partition_services(tmp_path, monkeypatch)
    services.config.pipeline_submission_upload_root = "s3://allowed/uploads"
    sign = Mock(return_value=SimpleNamespace(url="https://s3.example", file="file.txt", fields=[]))
    monkeypatch.setattr(pipeline_submission.S3Provider, "presigned_post", sign)
    upload = pipeline_submission.create_submission_folder_upload(services, "toy", "raw", _folder_files("a.txt", "nested/b.txt"))
    destinations = [call.args[0] for call in sign.call_args_list]
    assert destinations[0].rsplit("/", 1)[0] == destinations[1].split("/nested/")[0]
    assert sign.call_args.kwargs["min_bytes"] == 0
    client = Mock()
    objects = [{"Key": pipeline_submission._s3_parts(uri)[1], "Size": 3} for uri in destinations]
    client.get_paginator.return_value.paginate.return_value = [{"Contents": objects[:1]}, {"Contents": objects[1:]}]
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    source = SubmissionDatasetInput(name="raw", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id)
    location = _decode_upload(services, PipelineSubmissionInput(name="toy"), source, partitioned=True)
    assert location.startswith("s3://allowed/uploads/") and location.endswith("/")
    client.get_paginator.return_value.paginate.assert_called_once_with(Bucket="allowed", Prefix=pipeline_submission._s3_parts(location)[1])
    client.head_object.assert_not_called()
    objects[1]["Size"] = 2
    with pytest.raises(InvalidPipeline, match="wrong size"):
        _decode_upload(services, PipelineSubmissionInput(name="toy"), source, partitioned=True)


def test_folder_token_tampering_and_expiry(tmp_path, monkeypatch):
    services, _ = _partition_services(tmp_path, monkeypatch)
    upload = pipeline_submission.create_submission_folder_upload(services, "toy", "raw", _folder_files("a.txt"))
    config = services.config
    payload = jwt.decode(upload.upload_id, config.local_file_provider_jwt_secret_key, algorithms=[config.local_file_provider_jwt_algorithm])
    payload["files"][0]["size"] = 2
    tampered = jwt.encode(payload, "different-key", algorithm=config.local_file_provider_jwt_algorithm)
    payload["exp"] = 1
    expired = jwt.encode(payload, config.local_file_provider_jwt_secret_key, algorithm=config.local_file_provider_jwt_algorithm)
    for token in (tampered, expired):
        source = SubmissionDatasetInput(name="raw", method=SubmissionInputMethod.UPLOAD, upload_id=token)
        with pytest.raises(InvalidPipeline, match="invalid or expired"):
            _decode_upload(services, PipelineSubmissionInput(name="toy"), source, partitioned=True)


def test_versioned_partition_discovery_checks_underlying_files(tmp_path):
    root = tmp_path / "source"
    partition = root / "a.txt" / "2026-01-01"
    partition.mkdir(parents=True)
    (partition / "a.txt").write_text("data")
    config = {"type": "partitions.PartitionedDataset", "dataset": {"type": "text.TextDataset", "versioned": True},
              "path": str(root), "filename_suffix": ".txt"}
    assert pipeline_submission._check_partitioned_location("raw", config, str(root)) == str(root)


def test_s3_suffix_discovery_uses_catalog_settings_without_loading(monkeypatch):
    from kedro_datasets.partitions import PartitionedDataset
    filesystem = Mock()
    filesystem.sep = "/"
    filesystem.find.return_value = ["allowed/input/folder/file.csv", "allowed/input/folder/nested/file.txt"]
    filesystem.isfile.return_value = True
    monkeypatch.setattr(PartitionedDataset, "_filesystem", property(lambda self: filesystem))
    config = {"type": "partitions.PartitionedDataset", "dataset": "text.TextDataset", "path": "s3://allowed/input/folder/",
              "filename_suffix": ".txt", "load_args": {"maxdepth": 3}}
    assert pipeline_submission._check_partitioned_location("raw", config, config["path"]) == config["path"]
    filesystem.find.assert_called_once_with("s3://allowed/input/folder/", maxdepth=3)
    filesystem.isfile.assert_called_once_with("allowed/input/folder/nested/file.txt")
    filesystem.open.assert_not_called()


@pytest.mark.parametrize("min_bytes", [0, 1])
def test_s3_upload_policy_supports_empty_folder_files_and_preserves_single_file_minimum(monkeypatch, min_bytes):
    client = Mock()
    client.generate_presigned_post.return_value = {"url": "https://s3.example/upload", "fields": {}}
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    options = {"min_bytes": 0} if min_bytes == 0 else {}
    result = pipeline_submission.S3Provider.presigned_post("s3://bucket/folder/file.txt", 3600, max_bytes=100, **options)
    assert result is not None
    assert client.generate_presigned_post.call_args.kwargs["Conditions"] == [["content-length-range", min_bytes, 100]]


def _derived_services(tmp_path, monkeypatch):
    from kedro_graphql.dataset_input_derivations import DatasetInputDerivation
    services = _services(tmp_path, monkeypatch)
    catalog, _ = pipeline_submission.load_pipeline_configuration()
    catalog["raw_index"] = {"type": "text.TextDataset", "filepath": "/tmp/raw.txt.bai"}
    services.metadata.pipelines["toy"] = Pipeline([
        node(lambda raw, index: raw, ["raw", "raw_index"], "out", name="analyze"),
    ])
    services.config.dataset_input_derivations = [DatasetInputDerivation(
        pipeline_name="toy", dataset_name="raw_index", source_dataset="raw", append_suffix=".bai",
    )]
    return services, catalog


def _derived_submission(**extra):
    return PipelineSubmissionInput(name="toy", inputs=[SubmissionDatasetInput(
        name="raw", method=SubmissionInputMethod.S3_URI, s3_uri="s3://allowed/input/sample.bam", **extra,
    )])


def test_derived_metadata_and_concrete_catalog_paths(tmp_path, monkeypatch):
    services, original = _derived_services(tmp_path, monkeypatch)
    descriptor = next(item for item in build_submission_form(services, "toy").inputs if item.name == "raw_index")
    assert descriptor.derivation.source_dataset == "raw"
    assert descriptor.derivation.append_suffix == ".bai"
    client = Mock()
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    prepared, errors, _, resolved = _prepare_submission(services, _derived_submission())
    assert not errors
    paths = {item.name: json.loads(item.config)["filepath"] for item in prepared.data_catalog}
    assert paths == {"raw": "s3://allowed/input/sample.bam", "raw_index": "s3://allowed/input/sample.bam.bai"}
    assert [(item.name, item.s3_uri) for item in resolved] == [("raw_index", paths["raw_index"])]
    assert [call.kwargs["Key"] for call in client.head_object.call_args_list] == ["input/sample.bam", "input/sample.bam.bai"]
    assert original["raw_index"]["filepath"] == "/tmp/raw.txt.bai"


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_key", ["input/sample.bam", "input/sample.bam.bai"])
async def test_derived_validation_checks_both_objects_and_returns_failed_candidate(tmp_path, monkeypatch, failed_key):
    from botocore.exceptions import ClientError
    services, _ = _derived_services(tmp_path, monkeypatch)
    client = Mock()
    def head(**kwargs):
        if kwargs["Key"] == failed_key:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {"ContentLength": 3}
    client.head_object.side_effect = head
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    result = await validate_pipeline_submission(services, _derived_submission())
    assert not result.valid
    assert result.errors[0].path == ("raw" if failed_key.endswith(".bam") else "raw_index")
    assert result.resolved_inputs[0].s3_uri == "s3://allowed/input/sample.bam.bai"
    assert client.head_object.call_count == 2


@pytest.mark.parametrize("index_uri", ["s3://allowed/input/sample.bam.bai", "s3://allowed/input/different.bai"])
def test_explicit_target_overrides_derivation(tmp_path, monkeypatch, index_uri):
    services, _ = _derived_services(tmp_path, monkeypatch)
    checked = Mock(side_effect=lambda config, uri: uri)
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", checked)
    submission = _derived_submission()
    submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.S3_URI,
                                                    s3_uri=index_uri))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert not errors and not resolved
    assert {item.name: json.loads(item.config)["filepath"] for item in prepared.data_catalog} == {
        "raw": "s3://allowed/input/sample.bam", "raw_index": index_uri,
    }
    assert [call.args[1] for call in checked.call_args_list] == ["s3://allowed/input/sample.bam", index_uri]


def test_missing_derivation_source_and_target_scope_are_validated(tmp_path, monkeypatch):
    services, _ = _derived_services(tmp_path, monkeypatch)
    prepared, errors, _, resolved = _prepare_submission(services, PipelineSubmissionInput(name="toy"))
    assert prepared is None and not resolved
    assert any(error.path == "raw" for error in errors)
    client = Mock()
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    services.config.pipeline_submission_s3_allowed_prefixes = ["s3://allowed/input/sample.bam"]
    prepared, errors, _, _ = _prepare_submission(services, _derived_submission())
    assert prepared is None
    assert any(error.path == "raw_index" and "outside" in error.message for error in errors)


def test_upload_sources_keep_explicit_index_input(tmp_path, monkeypatch):
    from pathlib import Path
    services, _ = _derived_services(tmp_path, monkeypatch)
    upload = create_submission_upload(services, "toy", "raw", "sample.bam")
    payload = jwt.decode(upload.upload_id, services.config.local_file_provider_jwt_secret_key,
                         algorithms=[services.config.local_file_provider_jwt_algorithm])
    path = Path(payload["filepath"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"bam")
    submission = PipelineSubmissionInput(name="toy", inputs=[SubmissionDatasetInput(
        name="raw", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id,
    )])
    _, errors, _, resolved = _prepare_submission(services, submission)
    assert any(error.path == "raw_index" for error in errors)
    assert not resolved
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", lambda config, uri: uri)
    submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.S3_URI,
                                                    s3_uri="s3://allowed/input/explicit.bai"))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert not errors and not resolved
    paths = {item.name: json.loads(item.config)["filepath"] for item in prepared.data_catalog}
    assert paths == {"raw": str(path), "raw_index": "s3://allowed/input/explicit.bai"}


def test_derivation_respects_slice_producers_and_external_sources(tmp_path, monkeypatch):
    services, _ = _derived_services(tmp_path, monkeypatch)
    analyze = services.metadata.pipelines["toy"]
    services.metadata.pipelines["toy"] = Pipeline([
        node(lambda: "bam", None, "raw", name="produce"),
        node(lambda raw: raw, "raw", "raw_index", name="index"),
    ]) + analyze
    assert not build_submission_form(services, "toy").inputs
    sliced = build_submission_form(services, "toy", [PipelineSlice(slice=PipelineSliceType.NODE_NAMES, args=["analyze"])])
    assert next(input for input in sliced.inputs if input.name == "raw_index").derivation is not None
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", lambda config, uri: uri)
    submission = _derived_submission()
    submission.slices = [PipelineSlice(slice=PipelineSliceType.NODE_NAMES, args=["analyze"])]
    prepared, errors, _, _ = _prepare_submission(services, submission)
    assert not errors and {item.name for item in prepared.data_catalog} == {"raw", "raw_index"}
    # An external index whose BAM is produced in this slice still needs an explicit input.
    mixed = build_submission_form(services, "toy", [PipelineSlice(slice=PipelineSliceType.NODE_NAMES, args=["produce", "analyze"])])
    assert [item.name for item in mixed.inputs] == ["raw_index"]
    assert mixed.inputs[0].derivation is None


@pytest.mark.asyncio
async def test_validate_and_submit_use_identical_derivation_resolution(tmp_path, monkeypatch):
    services, _ = _derived_services(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", lambda config, uri: uri)
    create = AsyncMock(return_value=SimpleNamespace(id="created"))
    monkeypatch.setattr("kedro_graphql.pipeline_service.create_pipeline", create)
    submission = _derived_submission()
    validation = await validate_pipeline_submission(services, submission)
    assert validation.valid and validation.resolved_inputs[0].s3_uri.endswith(".bam.bai")
    await pipeline_submission.submit_pipeline(services, submission, None)
    for call in create.await_args_list:
        entries = {item.name: json.loads(item.config)["filepath"] for item in call.args[1].data_catalog}
        assert entries == {"raw": "s3://allowed/input/sample.bam", "raw_index": "s3://allowed/input/sample.bam.bai"}
    assert create.await_args_list[0].kwargs["dry_run"] is True
    assert "dry_run" not in create.await_args_list[1].kwargs


@pytest.mark.asyncio
async def test_derived_paths_survive_application_validation_errors(tmp_path, monkeypatch):
    services, _ = _derived_services(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", lambda config, uri: uri)
    services.config.pipeline_submission_transform = "kedro_graphql.pipeline_submission._test_transform"
    def reject(*args):
        raise InvalidPipeline("A sample barcode is required.")
    monkeypatch.setattr(pipeline_submission, "_test_transform", reject, raising=False)
    result = await validate_pipeline_submission(services, _derived_submission())
    assert not result.valid
    assert result.errors[0].path is None
    assert result.resolved_inputs[0].s3_uri == "s3://allowed/input/sample.bam.bai"


@pytest.mark.parametrize("from_suffix,uri,expected", [
    (".bam", "s3://allowed/input/sample.bam", "s3://allowed/input/sample.bai"),
    (".bam.gz", "s3://allowed/input/sample.bam.gz", "s3://allowed/input/sample.bai"),
    (".bam", "s3://allowed/input/folder.bam/sample.bam.bam", "s3://allowed/input/folder.bam/sample.bam.bai"),
])
def test_replace_suffix_derives_concrete_catalog_paths(tmp_path, monkeypatch, from_suffix, uri, expected):
    from kedro_graphql.dataset_input_derivations import DatasetInputDerivation
    services, _ = _derived_services(tmp_path, monkeypatch)
    services.config.dataset_input_derivations = [DatasetInputDerivation(
        pipeline_name="toy", dataset_name="raw_index", source_dataset="raw",
        replace_suffix={"from_suffix": from_suffix, "to_suffix": ".bai"},
    )]
    form = build_submission_form(services, "toy")
    rule = next(item for item in form.inputs if item.name == "raw_index").derivation
    assert rule.append_suffix is None
    assert rule.replace_suffix.from_suffix == from_suffix
    checked = Mock(side_effect=lambda config, location: location)
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", checked)
    submission = _derived_submission()
    submission.inputs[0].s3_uri = uri
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert not errors
    assert resolved[0].s3_uri == expected
    paths = {item.name: json.loads(item.config)["filepath"] for item in prepared.data_catalog}
    assert paths == {"raw": uri, "raw_index": expected}
    assert [call.args[1] for call in checked.call_args_list] == [uri, expected]


@pytest.mark.asyncio
@pytest.mark.parametrize("uri", ["s3://allowed/input/sample.BAM", "s3://allowed/input/sample.bam.other"])
async def test_replace_suffix_mismatches_report_target_error(tmp_path, monkeypatch, uri):
    from kedro_graphql.dataset_input_derivations import DatasetInputDerivation
    services, _ = _derived_services(tmp_path, monkeypatch)
    services.config.dataset_input_derivations = [DatasetInputDerivation(
        pipeline_name="toy", dataset_name="raw_index", source_dataset="raw",
        replace_suffix={"from_suffix": ".bam", "to_suffix": ".bai"},
    )]
    checked = Mock(side_effect=lambda config, location: location)
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", checked)
    submission = _derived_submission()
    submission.inputs[0].s3_uri = uri
    result = await validate_pipeline_submission(services, submission)
    assert not result.valid
    assert not result.resolved_inputs
    assert [(error.path, error.message) for error in result.errors] == [
        ("raw_index", "Source URI must end with '.bam' for suffix replacement."),
    ]
    checked.assert_called_once_with(services.config, uri)


@pytest.mark.parametrize("index_uri", ["", "s3://outside/index.bai"])
def test_explicit_target_is_validated_without_automatic_derivation(tmp_path, monkeypatch, index_uri):
    services, _ = _derived_services(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=Mock()))
    submission = _derived_submission()
    submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.S3_URI, s3_uri=index_uri))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert prepared is None and not resolved
    assert any(error.path == "raw_index" for error in errors)


def test_explicit_upload_target_overrides_s3_derivation(tmp_path, monkeypatch):
    from pathlib import Path
    services, _ = _derived_services(tmp_path, monkeypatch)
    upload = create_submission_upload(services, "toy", "raw_index", "custom.bai")
    payload = jwt.decode(upload.upload_id, services.config.local_file_provider_jwt_secret_key,
                         algorithms=[services.config.local_file_provider_jwt_algorithm])
    path = Path(payload["filepath"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"index")
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", lambda config, uri: uri)
    submission = _derived_submission()
    submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.UPLOAD, upload_id=upload.upload_id))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert not errors and not resolved
    assert json.loads(next(item.config for item in prepared.data_catalog if item.name == "raw_index"))["filepath"] == str(path)


def test_explicit_target_bypasses_replace_suffix_mismatch(tmp_path, monkeypatch):
    from kedro_graphql.dataset_input_derivations import DatasetInputDerivation
    services, _ = _derived_services(tmp_path, monkeypatch)
    services.config.dataset_input_derivations = [DatasetInputDerivation(
        pipeline_name="toy", dataset_name="raw_index", source_dataset="raw",
        replace_suffix={"from_suffix": ".bam", "to_suffix": ".bai"},
    )]
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", lambda config, uri: uri)
    submission = _derived_submission()
    submission.inputs[0].s3_uri = "s3://allowed/input/nonmatching.dat"
    submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.S3_URI,
                                                    s3_uri="s3://allowed/input/custom.bai"))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert prepared is not None and not errors and not resolved


@pytest.mark.parametrize("pattern,replacement,uri,expected", [
    (r"(?P<stem>[^/]+)\.bam$", r"\g<stem>.bai", "s3://allowed/input/sample.bam", "s3://allowed/input/sample.bai"),
    (r"(?i)\.bam$", ".bai", "s3://allowed/input/sample.BAM", "s3://allowed/input/sample.bai"),
    (r"(sample)\.bam$", r"\1.index.bai", "s3://allowed/input/sample.bam", "s3://allowed/input/sample.index.bai"),
    ("sample", "index", "s3://allowed/input/sample/sample.bam", "s3://allowed/input/index/index.bam"),
    (r"\.bam$", ".bai", "s3://allowed/input/sample.dat", "s3://allowed/input/sample.dat"),
    (r"\.bam$", "", "s3://allowed/input/sample.bam", "s3://allowed/input/sample"),
])
def test_python_regex_derivation_resolves_and_validates_catalog_paths(tmp_path, monkeypatch, pattern, replacement, uri, expected):
    from kedro_graphql.dataset_input_derivations import DatasetInputDerivation
    services, _ = _derived_services(tmp_path, monkeypatch)
    services.config.dataset_input_derivations = [DatasetInputDerivation(
        pipeline_name="toy", dataset_name="raw_index", source_dataset="raw",
        regex_sub={"pattern": pattern, "replacement": replacement},
    )]
    form = build_submission_form(services, "toy")
    rule = next(item for item in form.inputs if item.name == "raw_index").derivation
    assert rule.regex_sub.pattern == pattern and rule.regex_sub.replacement == replacement
    checked = Mock(side_effect=lambda config, location: location)
    monkeypatch.setattr(pipeline_submission, "_check_s3_uri", checked)
    submission = _derived_submission()
    submission.inputs[0].s3_uri = uri
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert not errors and resolved[0].s3_uri == expected
    assert json.loads(next(item.config for item in prepared.data_catalog if item.name == "raw_index"))["filepath"] == expected
    assert [call.args[1] for call in checked.call_args_list] == [uri, expected]


def test_regex_outputs_still_require_s3_scope_and_explicit_overrides_bypass_regex(tmp_path, monkeypatch):
    from kedro_graphql.dataset_input_derivations import DatasetInputDerivation
    services, _ = _derived_services(tmp_path, monkeypatch)
    services.config.dataset_input_derivations = [DatasetInputDerivation(
        pipeline_name="toy", dataset_name="raw_index", source_dataset="raw",
        regex_sub={"pattern": "^s3://allowed/", "replacement": "s3://outside/"},
    )]
    client = Mock()
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    submission = _derived_submission()
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert prepared is None
    assert any(error.path == "raw_index" and "outside" in error.message for error in errors)
    assert resolved[0].s3_uri == "s3://outside/input/sample.bam"
    submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.S3_URI,
                                                    s3_uri="s3://allowed/input/custom.bai"))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert prepared is not None and not errors and not resolved


@pytest.mark.parametrize("override", [False, True])
def test_chained_derivations_resolve_in_order_and_use_intermediate_overrides(tmp_path, monkeypatch, override):
    services, catalog = _derived_services(tmp_path, monkeypatch)
    catalog["dedup_index"] = {"type": "text.TextDataset", "filepath": "/tmp/dedup.bai"}
    services.metadata.pipelines["toy"] = Pipeline([
        node(lambda *inputs: inputs[0], ["raw", "raw_index", "dedup_index"], "out", name="analyze"),
    ])
    services.config.dataset_input_derivations = load_config({"dataset_input_derivations": [
        {"pipeline_name": "toy", "dataset_name": "dedup_index", "source_dataset": "raw_index",
         "regex_sub": {"pattern": "full", "replacement": "dedup"}},
        {"pipeline_name": "toy", "dataset_name": "raw_index", "source_dataset": "raw", "append_suffix": ".bai"},
    ]}).dataset_input_derivations
    submission = _derived_submission()
    submission.inputs[0].s3_uri = "s3://allowed/input/full.bam"
    if override:
        submission.inputs.append(SubmissionDatasetInput(name="raw_index", method=SubmissionInputMethod.S3_URI,
                                                       s3_uri="s3://allowed/input/full.custom.bai"))
    client = Mock()
    monkeypatch.setattr(pipeline_submission.boto3, "client", Mock(return_value=client))
    prepared, errors, _, resolved = _prepare_submission(services, submission)
    assert not errors
    paths = {item.name: json.loads(item.config)["filepath"] for item in prepared.data_catalog}
    assert paths["raw_index"] == ("s3://allowed/input/full.custom.bai" if override else "s3://allowed/input/full.bam.bai")
    assert paths["dedup_index"] == paths["raw_index"].replace("full", "dedup")
    assert {item.name for item in resolved} == ({"dedup_index"} if override else {"raw_index", "dedup_index"})
    assert len(client.head_object.call_args_list) == 3
    from botocore.exceptions import ClientError
    for failed_name in ("raw_index", "dedup_index"):
        def check_object(**kwargs):
            if kwargs["Key"] == paths[failed_name].split("/", 3)[3]:
                raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        client.head_object.side_effect = check_object
        _, failed_errors, _, candidates = _prepare_submission(services, submission)
        assert any(error.path == failed_name for error in failed_errors)
        assert next(item.s3_uri for item in candidates if item.name == "dedup_index") == paths["dedup_index"]
