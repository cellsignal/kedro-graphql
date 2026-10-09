import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from kedro_graphql.config import KedroGraphQLConfig, load_config


def test_defaults_are_typed():
    with patch.dict("os.environ", {}, clear=True), patch(
        "kedro_graphql.config.dotenv_values", return_value={}
    ):
        config = load_config()

    assert isinstance(config, KedroGraphQLConfig)
    assert config.app == "kedro_graphql.asgi.create_app"
    assert config.imports == ["kedro_graphql.plugins.plugins"]
    assert config.celery_abort_polling_interval == 5
    assert config.pipeline_submission_max_bytes == 1_048_576


def test_configuration_precedence(tmp_path):
    spec = tmp_path / "api.yml"
    spec.write_text("config:\n  mongo_uri: mongodb://yaml:27017/\n")
    dotenv = {
        "KEDRO_GRAPHQL_APP_TITLE": "dotenv",
        "KEDRO_GRAPHQL_BROKER": "redis://dotenv:6379",
    }
    environment = {
        "KEDRO_GRAPHQL_APP_TITLE": "environment",
        "KEDRO_GRAPHQL_BROKER": "redis://environment:6379",
    }
    cli = {
        "KEDRO_GRAPHQL_APP_TITLE": "cli",
        "KEDRO_GRAPHQL_MONGO_URI": "mongodb://cli:27017/",
    }

    with patch.dict("os.environ", environment, clear=True), patch(
        "kedro_graphql.config.dotenv_values", return_value=dotenv
    ):
        config = load_config(cli, spec)

    assert config.app_title == "cli"
    assert config.broker == "redis://environment:6379"
    assert config.mongo_uri == "mongodb://yaml:27017/"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("one,two", ["one", "two"]),
        ('["one", "two"]', ["one", "two"]),
        ("", []),
    ],
)
def test_list_parsing(raw, expected):
    assert KedroGraphQLConfig(imports=raw).imports == expected


def test_mapping_parsing():
    value = {"admin": ["read_pipeline"]}
    config = KedroGraphQLConfig(
        permissions_role_to_action_map=json.dumps(value)
    )
    assert config.permissions_role_to_action_map == value

    sources = {"example00": "/runtime/pipelines/example00"}
    config = KedroGraphQLConfig(pipeline_config_sources=json.dumps(sources))
    assert config.pipeline_config_sources == sources


def test_invalid_structured_value_fails():
    with pytest.raises(ValidationError):
        KedroGraphQLConfig(events_config="not json")


def test_submission_limit_must_be_positive():
    with pytest.raises(ValidationError):
        KedroGraphQLConfig(pipeline_submission_max_bytes=0)


def test_unknown_yaml_setting_fails(tmp_path):
    spec = tmp_path / "api.yml"
    spec.write_text("config:\n  typo_setting: true\n")
    with patch.dict("os.environ", {}, clear=True), patch(
        "kedro_graphql.config.dotenv_values", return_value={}
    ), pytest.raises(ValidationError):
        load_config(api_spec=spec)


def test_pipeline_runners_parse_json_and_default_to_sequential():
    config = KedroGraphQLConfig(pipeline_runners='{"toy": "custom.ArgoRunner"}')
    assert config.pipeline_runners == {"toy": "custom.ArgoRunner"}
    assert config.runner == "kedro.runner.SequentialRunner"
    assert KedroGraphQLConfig().pipeline_runners == {}


@pytest.mark.parametrize("setting", [
    "pipeline_submission_parameter_allowlists",
    "pipeline_submission_parameter_disallowlists",
])
def test_parameter_visibility_config_loads_yaml_and_environment(setting, tmp_path):
    rules = {"toy": ["settings.amount"], "aggregate": []}
    alias = f"KEDRO_GRAPHQL_{setting.upper()}"
    spec = tmp_path / "api.yml"
    spec.write_text(f"config:\n  {setting}: {json.dumps(rules)}\n")
    with patch.dict("os.environ", {}, clear=True), patch(
        "kedro_graphql.config.dotenv_values", return_value={}
    ):
        assert getattr(load_config(api_spec=spec), setting) == rules
    with patch.dict("os.environ", {alias: json.dumps(rules)}, clear=True), patch(
        "kedro_graphql.config.dotenv_values", return_value={}
    ):
        assert getattr(load_config(), setting) == rules
    assert getattr(KedroGraphQLConfig(), setting) == {}


@pytest.mark.parametrize("setting", [
    "pipeline_submission_parameter_allowlists",
    "pipeline_submission_parameter_disallowlists",
])
@pytest.mark.parametrize("path", ["", " ", ".settings", "settings.", "settings..amount"])
def test_parameter_visibility_rejects_invalid_paths(setting, path):
    with pytest.raises(ValidationError, match="Invalid parameter path"):
        KedroGraphQLConfig(**{setting: {"toy": [path]}})


@pytest.mark.parametrize("key", [
    "pipeline_submission_partition_upload_max_files",
    "pipeline_submission_partition_upload_max_size_mb",
])
def test_partition_upload_limits_are_positive(key):
    from kedro_graphql.config import load_config
    with pytest.raises(ValueError):
        load_config({key: 0})
    assert getattr(load_config({key: 2}), key) == 2


def _derivation(**values):
    return {"pipeline_name": "toy", "dataset_name": "index", "source_dataset": "bam", "append_suffix": ".bai", **values}


@pytest.mark.parametrize("registrations", [
    [_derivation(), _derivation()],
    [_derivation(source_dataset="index")],
    [_derivation(), _derivation(dataset_name="bam", source_dataset="index")],
    [_derivation(append_suffix="")], [_derivation(append_suffix="/index")],
    [_derivation(append_suffix="?key=foo")], [_derivation(dataset_name=" ")],
    [_derivation(extra="unsupported")],
])
def test_invalid_derivation_registrations_are_rejected(registrations):
    with pytest.raises(ValidationError):
        load_config({"dataset_input_derivations": registrations})


def test_derivation_config_accepts_json_and_independent_pipeline_targets():
    config = load_config({"dataset_input_derivations": json.dumps([
        _derivation(), _derivation(pipeline_name="other"),
    ])})
    assert len(config.dataset_input_derivations) == 2
    assert config.dataset_input_derivations[0].append_suffix == ".bai"


def test_derivation_registrations_require_known_graph_references():
    from kedro.pipeline import Pipeline, node
    from kedro_graphql.dataset_input_derivations import validate_dataset_input_derivations
    config = load_config({"dataset_input_derivations": [_derivation()]})
    graph = Pipeline([node(lambda bam, index: bam, ["bam", "index"], "out")])
    validate_dataset_input_derivations(config.dataset_input_derivations, {"toy": graph})
    with pytest.raises(ValueError, match="Unknown derivation pipeline"):
        validate_dataset_input_derivations(config.dataset_input_derivations, {})
    graph = Pipeline([node(lambda bam: bam, "bam", "out")])
    with pytest.raises(ValueError, match="Unknown derivation dataset"):
        validate_dataset_input_derivations(config.dataset_input_derivations, {"toy": graph})


@pytest.mark.parametrize("rule", [
    {"pipeline_name": "toy", "dataset_name": "index", "source_dataset": "bam"},
    _derivation(replace_suffix={"from_suffix": ".bam", "to_suffix": ".bai"}),
    _derivation(append_suffix=None, replace_suffix={"from_suffix": "", "to_suffix": ".bai"}),
    _derivation(append_suffix=None, replace_suffix={"from_suffix": ".bam", "to_suffix": ""}),
    _derivation(append_suffix=None, replace_suffix={"from_suffix": ".bam", "to_suffix": "/index"}),
    _derivation(append_suffix=None, replace_suffix={"from_suffix": ".bam", "to_suffix": ".bai", "extra": True}),
])
def test_derivation_replacement_requires_one_safe_operation(rule):
    with pytest.raises(ValidationError):
        load_config({"dataset_input_derivations": [rule]})


def test_derivation_replacement_config_is_typed():
    config = load_config({"dataset_input_derivations": [_derivation(
        append_suffix=None, replace_suffix={"from_suffix": ".bam.gz", "to_suffix": ".bai"},
    )]})
    rule = config.dataset_input_derivations[0]
    assert rule.append_suffix is None
    assert rule.replace_suffix.from_suffix == ".bam.gz"
    assert rule.replace_suffix.to_suffix == ".bai"


@pytest.mark.parametrize("regex_sub", [
    {"pattern": "[", "replacement": ".bai"},
    {"pattern": "", "replacement": ".bai"},
    {"pattern": r"\.bam$", "replacement": r"\g<missing>"},
    {"pattern": r"\.bam$", "replacement": r"\2"},
    {"pattern": r"\.bam$", "replacement": r"\q"},
    {"pattern": r"\.bam$", "replacement": ".bai", "flags": "IGNORECASE"},
])
def test_regex_derivation_rejects_invalid_python_patterns_and_replacements(regex_sub):
    with pytest.raises(ValidationError, match="regex|pattern|flags"):
        load_config({"dataset_input_derivations": [_derivation(append_suffix=None, regex_sub=regex_sub)]})


def test_regex_derivation_accepts_python_groups_inline_flags_and_empty_replacement():
    config = load_config({"dataset_input_derivations": [_derivation(
        append_suffix=None, regex_sub={"pattern": r"(?i)(?P<name>[^/]+)\.bam$", "replacement": r"\g<name>.bai"},
    )]})
    assert config.dataset_input_derivations[0].regex_sub.replacement == r"\g<name>.bai"
    config = load_config({"dataset_input_derivations": [_derivation(
        append_suffix=None, regex_sub={"pattern": r"\.bam$", "replacement": ""},
    )]})
    assert config.dataset_input_derivations[0].regex_sub.replacement == ""


@pytest.mark.parametrize("other", [
    {"append_suffix": ".bai"},
    {"replace_suffix": {"from_suffix": ".bam", "to_suffix": ".bai"}},
])
def test_regex_derivation_cannot_be_combined_with_another_operation(other):
    rule = _derivation(**{"append_suffix": None, "regex_sub": {"pattern": r"\.bam$", "replacement": ".bai"}, **other})
    with pytest.raises(ValidationError, match="exactly one"):
        load_config({"dataset_input_derivations": [rule]})


def test_derivation_chains_are_sorted_by_dependency():
    config = load_config({"dataset_input_derivations": [
        _derivation(dataset_name="dedup_index", source_dataset="index"),
        _derivation(),
    ]})
    assert [rule.dataset_name for rule in config.dataset_input_derivations] == ["index", "dedup_index"]
