import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _alias(name: str) -> str:
    return f"KEDRO_GRAPHQL_{name.upper()}"


class KedroGraphQLConfig(BaseModel):
    """Validated configuration shared by the API and worker."""

    model_config = ConfigDict(alias_generator=_alias, populate_by_name=True, extra="forbid")

    app: str = "kedro_graphql.asgi.create_app"
    app_description: str = "A tool for serving kedro projects as a GraphQL API"
    app_title: str = "Kedro GraphQL API"
    always_hooks: list[str] = Field(default_factory=list)
    backend: str = "kedro_graphql.backends.mongodb.MongoBackend"
    broker: str = "redis://localhost"
    celery_result_backend: str = "redis://localhost"
    celery_abort_polling_interval: float = 5
    celery_abort_grace_period: float = 60
    client_uri_graphql: str = "http://localhost:5000/graphql"
    client_uri_ws: str = "ws://localhost:5000/graphql"
    conf_source: str | None = None
    dataset_filepath_masks: list[dict[str, str]] = Field(default_factory=list)
    dataset_filepath_allowed_roots: list[str] = Field(default_factory=list)
    deprecations_docs: str | None = None
    env: str = "local"
    events_config: dict[str, dict[str, Any]] | None = None
    imports: list[str] = Field(default_factory=lambda: ["kedro_graphql.plugins.plugins"])
    local_file_provider_download_allowed_roots: list[str] = Field(
        default_factory=lambda: ["./data", "/var", "/tmp"]
    )
    local_file_provider_jwt_algorithm: str = "HS256"
    local_file_provider_jwt_secret_key: str = "my-secret-key"
    local_file_provider_server_url: str = "http://localhost:5000"
    local_file_provider_upload_allowed_roots: list[str] = Field(
        default_factory=lambda: ["./data"]
    )
    local_file_provider_upload_max_file_size_mb: int = 10
    log_path_prefix: str | None = None
    log_tmp_dir: str = str(Path(tempfile.gettempdir()) / "kedro-graphql")
    mongo_db_collection: str = "pipelines"
    mongo_db_name: str = "pipelines"
    mongo_uri: str = "mongodb://root:example@localhost:27017/"
    permissions: str = "kedro_graphql.permissions.IsAuthenticatedAlways"
    permissions_group_to_role_map: dict[str, str] = Field(
        default_factory=lambda: {"EXTERNAL_GROUP_NAME": "admin"}
    )
    permissions_role_to_action_map: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "admin": [
                "create_pipeline",
                "read_pipeline",
                "read_pipelines",
                "update_pipeline",
                "delete_pipeline",
                "read_pipeline_template",
                "read_pipeline_templates",
                "create_dataset",
                "read_dataset",
                "subscribe_to_events",
                "subscribe_to_logs",
                "create_event",
            ]
        }
    )
    project_name: str | None = Field(default=None, alias="KEDRO_PROJECT_NAME")
    project_version: str = "None"
    root_path: str = ""
    runner: str = "kedro.runner.SequentialRunner"
    signed_url_max_expires_in_sec: int = 43200
    signed_url_provider: str = "kedro_graphql.signed_url.s3_provider.S3Provider"

    @field_validator(
        "always_hooks",
        "imports",
        "local_file_provider_download_allowed_roots",
        "local_file_provider_upload_allowed_roots",
        mode="before",
    )
    @classmethod
    def _parse_list(cls, value):
        if not isinstance(value, str):
            return value
        if not value.strip():
            return []
        if value.lstrip().startswith("["):
            return json.loads(value)
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator(
        "events_config",
        "dataset_filepath_masks",
        "dataset_filepath_allowed_roots",
        "permissions_group_to_role_map",
        "permissions_role_to_action_map",
        mode="before",
    )
    @classmethod
    def _parse_json(cls, value):
        return json.loads(value) if isinstance(value, str) else value


def load_api_spec(path: str | Path | None = None) -> dict[str, Any]:
    spec = path or os.environ.get("KEDRO_GRAPHQL_API_SPEC")
    if not spec:
        return {}
    with Path(spec).open() as stream:
        document = yaml.safe_load(stream) or {}
    return {_alias(key): value for key, value in document.get("config", {}).items()}


def load_config(
    cli_config: Mapping[str, Any] | None = None,
    api_spec: str | Path | None = None,
) -> KedroGraphQLConfig:
    """Load and validate configuration using the documented precedence order."""

    aliases = {
        field.alias or _alias(name)
        for name, field in KedroGraphQLConfig.model_fields.items()
    }
    dotenv = {key: value for key, value in dotenv_values(".env").items() if key in aliases}
    environment = {key: value for key, value in os.environ.items() if key in aliases}
    values = {
        **dotenv,
        **environment,
        **(cli_config or {}),
        **load_api_spec(api_spec),
    }
    return KedroGraphQLConfig.model_validate(values)
