from pathlib import Path
from unittest.mock import Mock

from strawberry.fastapi import BaseContext

from kedro_graphql.commands import start_worker
from kedro_graphql.config import KedroGraphQLConfig
from kedro_graphql.context import GraphQLContext
from kedro_graphql.project import load_project_metadata


def test_project_metadata_uses_configured_loader(monkeypatch):
    calls = {}

    class Loader:
        def __init__(self, **kwargs):
            calls.update(kwargs)

        def __getitem__(self, key):
            return {"catalog": {}, "parameters": {}}[key]

    monkeypatch.setattr("kedro_graphql.project.settings.CONFIG_LOADER_CLASS", Loader)
    monkeypatch.setattr("kedro_graphql.project.settings.CONFIG_LOADER_ARGS", {})
    monkeypatch.setattr("kedro_graphql.project.settings.CONF_SOURCE", "conf")

    metadata = load_project_metadata(Path("/project"), KedroGraphQLConfig(env="test"))

    assert calls == {"conf_source": "/project/conf", "env": "test"}
    assert metadata.catalog == {}
    assert metadata.parameters == {}


def test_app_contains_typed_services_without_session(mock_app):
    services = mock_app.state.services

    assert isinstance(services.config, KedroGraphQLConfig)
    assert services.metadata.pipelines
    assert not hasattr(mock_app, "kedro_session")


def test_graphql_context_satisfies_strawberry_contract():
    assert isinstance(GraphQLContext(Mock()), BaseContext)


def test_worker_does_not_build_web_application(monkeypatch):
    backend = object()
    worker = Mock()
    celery = Mock()
    celery.Worker.return_value = worker
    monkeypatch.setattr("kedro_graphql.commands.bootstrap_project", Mock())
    monkeypatch.setattr("kedro_graphql.commands.init_backend", Mock(return_value=backend))
    monkeypatch.setattr("kedro_graphql.commands.celery_app", Mock(return_value=celery))

    start_worker(KedroGraphQLConfig(), Path("/project"))

    worker.start.assert_called_once_with()
