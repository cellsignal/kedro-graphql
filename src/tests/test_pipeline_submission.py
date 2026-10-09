from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import json

import jwt
import pytest
from kedro.pipeline import Pipeline, node

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

    pipeline_input, errors, outputs = _prepare_submission(services, submission)

    assert not errors
    assert outputs == ["out"]
    settings = next(parameter for parameter in pipeline_input.parameters if parameter.name == "settings")
    assert json.loads(settings.value)["values"] == [False, 2.5]
    assert json.loads(pipeline_input.data_catalog[0].config)["filepath"] == "s3://allowed/input/raw.txt"

    submission.parameters[0].value = [{"not": "a leaf"}]
    _, errors, _ = _prepare_submission(services, submission)
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
    pipeline_input, errors, managed = _prepare_submission(services, submission)
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
