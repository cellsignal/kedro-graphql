"""
Tests for the configuration system.

This module tests configuration precedence, complex data type parsing,
and edge cases for the kedro-graphql configuration system.
"""
import json
import os
import yaml
from unittest.mock import patch, mock_open
import pytest

from kedro_graphql.config import load_config, env_var_parser, load_api_spec, defaults


class TestConfigurationPrecedence:
    """Test configuration precedence order."""

    def test_defaults_only(self):
        """Test that defaults work when no other config is provided."""
        with patch.dict(os.environ, {}, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value={}), \
                patch('kedro_graphql.config.load_api_spec', return_value={}):

            config = load_config()
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Kedro GraphQL API"
            assert config["KEDRO_GRAPHQL_IMPORTS"] == ["kedro_graphql.plugins.plugins"]

    def test_env_var_overrides_defaults(self):
        """Test that environment variables override defaults."""
        env_vars = {
            "KEDRO_GRAPHQL_APP_TITLE": "Custom Title from Env",
            "KEDRO_GRAPHQL_MONGO_URI": "mongodb://custom:27017/"
        }

        with patch.dict(os.environ, env_vars, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value={}), \
                patch('kedro_graphql.config.load_api_spec', return_value={}):

            config = load_config()
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Custom Title from Env"
            assert config["KEDRO_GRAPHQL_MONGO_URI"] == "mongodb://custom:27017/"
            # Defaults should still be there for non-overridden values
            assert config["KEDRO_GRAPHQL_BACKEND"] == defaults["KEDRO_GRAPHQL_BACKEND"]

    def test_dotenv_overrides_defaults(self):
        """Test that .env file values override defaults."""
        dotenv_values = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from dotenv",
            "KEDRO_GRAPHQL_BROKER": "redis://dotenv:6379"
        }

        with patch.dict(os.environ, {}, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value=dotenv_values), \
                patch('kedro_graphql.config.load_api_spec', return_value={}):

            config = load_config()
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Title from dotenv"
            assert config["KEDRO_GRAPHQL_BROKER"] == "redis://dotenv:6379"

    def test_env_var_overrides_dotenv(self):
        """Test that environment variables override .env file values."""
        dotenv_values = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from dotenv",
            "KEDRO_GRAPHQL_BROKER": "redis://dotenv:6379"
        }
        env_vars = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from env var"
        }

        with patch.dict(os.environ, env_vars, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value=dotenv_values), \
                patch('kedro_graphql.config.load_api_spec', return_value={}):

            config = load_config()
            # env var wins
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Title from env var"
            # dotenv for non-conflicting
            assert config["KEDRO_GRAPHQL_BROKER"] == "redis://dotenv:6379"

    def test_cli_config_overrides_env_var(self):
        """Test that CLI config overrides environment variables."""
        env_vars = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from env var",
            "KEDRO_GRAPHQL_MONGO_URI": "mongodb://env:27017/"
        }
        cli_config = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from CLI"
        }

        with patch.dict(os.environ, env_vars, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value={}), \
                patch('kedro_graphql.config.load_api_spec', return_value={}):

            config = load_config(cli_config=cli_config)
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Title from CLI"  # CLI wins
            # env for non-conflicting
            assert config["KEDRO_GRAPHQL_MONGO_URI"] == "mongodb://env:27017/"

    def test_yaml_spec_overrides_cli_config(self):
        """Test that YAML spec has highest precedence."""
        env_vars = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from env var"
        }
        cli_config = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from CLI",
            "KEDRO_GRAPHQL_BROKER": "redis://cli:6379"
        }
        yaml_config = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from YAML"
        }

        with patch.dict(os.environ, env_vars, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value={}), \
                patch('kedro_graphql.config.load_api_spec', return_value=yaml_config):

            config = load_config(cli_config=cli_config)
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Title from YAML"  # YAML wins
            # CLI for non-conflicting
            assert config["KEDRO_GRAPHQL_BROKER"] == "redis://cli:6379"

    def test_full_precedence_chain(self):
        """Test complete precedence chain with all sources."""
        dotenv_values = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from dotenv",
            "KEDRO_GRAPHQL_BROKER": "redis://dotenv:6379",
            "KEDRO_GRAPHQL_BACKEND": "backend.from.dotenv"
        }
        env_vars = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from env",
            "KEDRO_GRAPHQL_BROKER": "redis://env:6379"
        }
        cli_config = {
            "KEDRO_GRAPHQL_APP_TITLE": "Title from CLI"
        }
        yaml_config = {
            "KEDRO_GRAPHQL_MONGO_URI": "mongodb://yaml:27017/"
        }

        with patch.dict(os.environ, env_vars, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value=dotenv_values), \
                patch('kedro_graphql.config.load_api_spec', return_value=yaml_config):

            config = load_config(cli_config=cli_config)

            # YAML spec (highest precedence)
            assert config["KEDRO_GRAPHQL_MONGO_URI"] == "mongodb://yaml:27017/"

            # CLI config (second highest)
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == "Title from CLI"

            # Environment variable (third)
            assert config["KEDRO_GRAPHQL_BROKER"] == "redis://env:6379"

            # .env file (fourth)
            assert config["KEDRO_GRAPHQL_BACKEND"] == "backend.from.dotenv"


class TestComplexDataTypeParsing:
    """Test parsing of complex data types (lists, dictionaries)."""

    def test_list_field_comma_separated_string(self):
        """Test parsing comma-separated strings for list fields."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": "module1.plugin,module2.plugin,module3.plugin",
            "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS": "./data,/var,/tmp"
        }

        parsed = env_var_parser(config)

        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == [
            "module1.plugin", "module2.plugin", "module3.plugin"]
        assert parsed["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS"] == [
            "./data", "/var", "/tmp"]

    def test_list_field_json_array(self):
        """Test parsing JSON arrays for list fields."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": '["module1.plugin", "module2.plugin"]',
            "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS": '["./data", "./uploads"]'
        }

        parsed = env_var_parser(config)

        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == ["module1.plugin", "module2.plugin"]
        assert parsed["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS"] == [
            "./data", "./uploads"]

    def test_list_field_single_value(self):
        """Test parsing single values that should become single-item lists."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": "single.module",
            "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS": "./uploads"
        }

        parsed = env_var_parser(config)

        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == ["single.module"]
        assert parsed["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_ALLOWED_ROOTS"] == [
            "./uploads"]

    def test_list_field_empty_string(self):
        """Test parsing empty strings for list fields."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": "",
            "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS": "   "  # whitespace only
        }

        parsed = env_var_parser(config)

        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == []
        assert parsed["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS"] == []

    def test_list_field_mixed_whitespace(self):
        """Test parsing comma-separated strings with mixed whitespace."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": " module1 , module2,  module3  ,, module4 ",
            "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS": "./data, /var , /tmp,"
        }

        parsed = env_var_parser(config)

        # Empty elements should be filtered out
        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == [
            "module1", "module2", "module3", "module4"]
        assert parsed["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_DOWNLOAD_ALLOWED_ROOTS"] == [
            "./data", "/var", "/tmp"]

    def test_json_field_dictionary(self):
        """Test parsing JSON dictionaries for complex fields."""
        config = {
            "KEDRO_GRAPHQL_EVENTS_CONFIG": '{"event1": {"source": "app", "type": "test"}}',
            "KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP": '{"admin": ["create", "read"], "viewer": ["read"]}'
        }

        parsed = env_var_parser(config)

        expected_events = {"event1": {"source": "app", "type": "test"}}
        expected_permissions = {"admin": ["create", "read"], "viewer": ["read"]}

        assert parsed["KEDRO_GRAPHQL_EVENTS_CONFIG"] == expected_events
        assert parsed["KEDRO_GRAPHQL_PERMISSIONS_ROLE_TO_ACTION_MAP"] == expected_permissions

    def test_json_field_invalid_json(self):
        """Test handling of invalid JSON in JSON fields."""
        config = {
            "KEDRO_GRAPHQL_EVENTS_CONFIG": '{"invalid": json}',  # Invalid JSON
            "KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP": 'not json at all'
        }

        with patch('kedro_graphql.config.logger') as mock_logger:
            parsed = env_var_parser(config)

            # Should remain as original string when JSON parsing fails
            assert parsed["KEDRO_GRAPHQL_EVENTS_CONFIG"] == '{"invalid": json}'
            assert parsed["KEDRO_GRAPHQL_PERMISSIONS_GROUP_TO_ROLE_MAP"] == 'not json at all'

            # Should log warnings
            assert mock_logger.warning.call_count == 2

    def test_list_field_complex_json_array(self):
        """Test parsing complex JSON arrays with nested objects."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": '[{"module": "plugin1", "config": {"enabled": true}}, "simple.module"]'
        }

        parsed = env_var_parser(config)

        expected = [{"module": "plugin1", "config": {"enabled": True}}, "simple.module"]
        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == expected

    def test_non_string_values_remain_unchanged(self):
        """Test that non-string values in config remain unchanged."""
        config = {
            "KEDRO_GRAPHQL_IMPORTS": ["already", "a", "list"],
            "KEDRO_GRAPHQL_EVENTS_CONFIG": {"already": "a", "dict": True},
            "KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB": 10,  # integer
        }

        parsed = env_var_parser(config)

        # Should remain as-is
        assert parsed["KEDRO_GRAPHQL_IMPORTS"] == ["already", "a", "list"]
        assert parsed["KEDRO_GRAPHQL_EVENTS_CONFIG"] == {"already": "a", "dict": True}
        assert parsed["KEDRO_GRAPHQL_LOCAL_FILE_PROVIDER_UPLOAD_MAX_FILE_SIZE_MB"] == 10


class TestYAMLSpecLoading:
    """Test YAML specification file loading."""

    def test_no_api_spec_env_var(self):
        """Test behavior when no API spec environment variable is set."""
        with patch.dict(os.environ, {}, clear=True):
            result = load_api_spec()
            assert result == {}

    def test_api_spec_file_not_found(self):
        """Test behavior when API spec file doesn't exist."""
        with patch.dict(os.environ, {"KEDRO_GRAPHQL_API_SPEC": "/nonexistent/file.yaml"}):
            with pytest.raises(FileNotFoundError):
                load_api_spec()

    def test_api_spec_invalid_yaml(self):
        """Test behavior with invalid YAML content."""
        invalid_yaml = "invalid: yaml: content: [unclosed"

        with patch.dict(os.environ, {"KEDRO_GRAPHQL_API_SPEC": "test.yaml"}), \
                patch("builtins.open", mock_open(read_data=invalid_yaml)), \
                patch('kedro_graphql.config.logger') as mock_logger:

            # Should handle gracefully and return empty dict
            result = load_api_spec()
            assert result == {}

            # Should log the error
            mock_logger.error.assert_called_once()

    def test_api_spec_valid_yaml(self):
        """Test successful YAML spec loading."""
        yaml_content = """
config:
  app_title: "Custom App Title"
  mongo_uri: "mongodb://yaml:27017/"
  imports:
    - "custom.plugin1"
    - "custom.plugin2"
  events_config:
    event1:
      source: "yaml.source"
      type: "yaml.event"
"""

        with patch.dict(os.environ, {"KEDRO_GRAPHQL_API_SPEC": "test.yaml"}), \
                patch("builtins.open", mock_open(read_data=yaml_content)), \
                patch('kedro_graphql.config.import_module') as mock_import:

            result = load_api_spec()

            expected = {
                "KEDRO_GRAPHQL_APP_TITLE": "Custom App Title",
                "KEDRO_GRAPHQL_MONGO_URI": "mongodb://yaml:27017/",
                "KEDRO_GRAPHQL_IMPORTS": ["custom.plugin1", "custom.plugin2"],
                "KEDRO_GRAPHQL_EVENTS_CONFIG": {
                    "event1": {"source": "yaml.source", "type": "yaml.event"}
                }
            }

            assert result == expected

            # Should import the specified modules
            mock_import.assert_any_call("custom.plugin1")
            mock_import.assert_any_call("custom.plugin2")

    def test_api_spec_imports_comma_separated_string(self):
        """Test YAML spec with imports as comma-separated string."""
        yaml_content = """
config:
  imports: "plugin1,plugin2,plugin3"
  app_title: "Test App"
"""

        with patch.dict(os.environ, {"KEDRO_GRAPHQL_API_SPEC": "test.yaml"}), \
                patch("builtins.open", mock_open(read_data=yaml_content)), \
                patch('kedro_graphql.config.import_module') as mock_import:

            result = load_api_spec()

            assert result["KEDRO_GRAPHQL_IMPORTS"] == "plugin1,plugin2,plugin3"

            # Should import each module
            mock_import.assert_any_call("plugin1")
            mock_import.assert_any_call("plugin2")
            mock_import.assert_any_call("plugin3")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_cli_config(self):
        """Test that empty cli_config works properly."""
        with patch.dict(os.environ, {}, clear=True), \
                patch('kedro_graphql.config.dotenv_values', return_value={}), \
                patch('kedro_graphql.config.load_api_spec', return_value={}):

            config = load_config(cli_config={})
            assert config["KEDRO_GRAPHQL_APP_TITLE"] == defaults["KEDRO_GRAPHQL_APP_TITLE"]
