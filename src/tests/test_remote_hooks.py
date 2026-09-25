import sys
import types
from unittest.mock import patch

import pytest
from kedro.framework.hooks import hook_impl

from kedro_graphql.remote_hooks import load_remote_hook_manager


class Plugin:
    def __init__(self):
        self.calls = []

    @hook_impl
    def before_pipeline_run(self, run_params, pipeline, catalog):
        self.calls.append("pipeline")

    @hook_impl
    def before_node_run(self, node, catalog, inputs, is_async, session_id):
        self.calls.append("node")


def _module(name, attribute, plugin):
    module = types.ModuleType(name)
    setattr(module, attribute, plugin)
    sys.modules[name] = module
    return module


def test_remote_loader_registers_only_specified_callbacks():
    plugin = Plugin()
    name = "tests.remote_hooks_only_node"
    _module(name, "plugin", plugin)
    try:
        manager = load_remote_hook_manager(
            [
                {
                    "name": "selected",
                    "module": name,
                    "attribute": "plugin",
                    "callbacks": ["before_node_run"],
                }
            ]
        )

        manager.hook.before_pipeline_run(run_params={}, pipeline=None, catalog=None)
        manager.hook.before_node_run(
            node=None, catalog=None, inputs={}, is_async=False, session_id="session"
        )
        assert plugin.calls == ["node"]
    finally:
        del sys.modules[name]


@pytest.mark.parametrize(
    "spec",
    [
        {"name": "selected"},
        {
            "name": "selected",
            "module": "tests.remote_hooks",
            "attribute": "plugin",
            "callbacks": ["before_pipeline_run"],
        },
        {
            "name": "selected",
            "module": "tests.remote_hooks",
            "attribute": "plugin",
            "callbacks": ["before_pipeline_run", "before_pipeline_run"],
        },
        {
            "name": "selected",
            "module": "tests.remote_hooks",
            "attribute": "plugin",
            "callbacks": ["before_pipeline_run", "not_a_kedro_callback"],
        },
    ],
)
def test_remote_loader_rejects_malformed_specs(spec):
    with pytest.raises((TypeError, ValueError)):
        load_remote_hook_manager([spec])


def test_remote_loader_warns_and_skips_missing_module(caplog):
    with caplog.at_level("WARNING"):
        manager = load_remote_hook_manager(
            [
                {
                    "name": "missing",
                    "module": "package_that_is_not_installed.remote_hooks",
                    "attribute": "plugin",
                    "callbacks": ["before_node_run"],
                }
            ]
        )

    assert "not installed" in caplog.text
    assert manager.get_plugins() == set()


def test_remote_loader_warns_and_skips_missing_attribute(caplog):
    name = "tests.remote_hooks_missing_attribute"
    _module(name, "other", Plugin())
    try:
        with caplog.at_level("WARNING"):
            manager = load_remote_hook_manager(
                [
                    {
                        "name": "missing",
                        "module": name,
                        "attribute": "plugin",
                        "callbacks": ["before_node_run"],
                    }
                ]
            )
    finally:
        del sys.modules[name]

    assert "is not available" in caplog.text
    assert manager.get_plugins() == set()


def test_remote_loader_propagates_import_error_inside_existing_module():
    error = ModuleNotFoundError("dependency missing", name="dependency")
    spec = {
        "name": "broken",
        "module": "existing.remote_hooks",
        "attribute": "plugin",
        "callbacks": ["before_node_run"],
    }
    with patch(
        "kedro_graphql.remote_hooks.importlib.import_module", side_effect=error
    ):
        with pytest.raises(ModuleNotFoundError, match="dependency missing"):
            load_remote_hook_manager([spec])


def test_remote_loader_propagates_existing_hook_error():
    class FailingPlugin:
        @hook_impl
        def before_node_run(self, node, catalog, inputs, is_async, session_id):
            raise RuntimeError("hook exploded")

    name = "tests.remote_hooks_failing"
    _module(name, "plugin", FailingPlugin())
    try:
        manager = load_remote_hook_manager(
            [
                {
                    "name": "failing",
                    "module": name,
                    "attribute": "plugin",
                    "callbacks": ["before_node_run"],
                }
            ]
        )
        with pytest.raises(RuntimeError, match="hook exploded"):
            manager.hook.before_node_run(
                node=None, catalog=None, inputs={}, is_async=False, session_id="session"
            )
    finally:
        del sys.modules[name]
