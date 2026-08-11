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


def test_invalid_structured_value_fails():
    with pytest.raises(ValidationError):
        KedroGraphQLConfig(events_config="not json")


def test_unknown_yaml_setting_fails(tmp_path):
    spec = tmp_path / "api.yml"
    spec.write_text("config:\n  typo_setting: true\n")
    with patch.dict("os.environ", {}, clear=True), patch(
        "kedro_graphql.config.dotenv_values", return_value={}
    ), pytest.raises(ValidationError):
        load_config(api_spec=spec)
