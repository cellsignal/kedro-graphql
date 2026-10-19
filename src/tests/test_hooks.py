import pytest
from kedro.framework.hooks import hook_impl

from kedro_graphql.hooks import (
    LOCAL_HOOK_CALLBACKS,
    hook_manager_for,
    remote_hook_specs_for,
)


class EntryPoint:
    def __init__(self, name, plugin, module="tests.test_hooks", attr="plugin"):
        self.name = name
        self.plugin = plugin
        self.module = module
        self.attr = attr

    def load(self):
        return self.plugin


class Hook:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    @hook_impl
    def before_pipeline_run(self, run_params, pipeline, catalog):
        self.calls.append(self.name)


def test_hook_manager_runs_only_selected_entry_point(mocker):
    calls = []
    selected = Hook("selected", calls)
    unselected = Hook("unselected", calls)
    mocker.patch(
        "kedro_graphql.hooks.entry_points",
        return_value=[EntryPoint("selected", selected), EntryPoint("unselected", unselected)],
    )

    manager = hook_manager_for(["selected"])
    manager.hook.before_pipeline_run(run_params={}, pipeline=None, catalog=None)

    assert calls == ["selected"]
    assert manager.get_plugins() == {selected}


def test_hook_manager_rejects_missing_entry_point(mocker):
    mocker.patch("kedro_graphql.hooks.entry_points", return_value=[])

    with pytest.raises(ValueError, match="Unavailable Kedro hooks"):
        hook_manager_for(["missing"])


def test_external_hooks_are_split_by_callback_scope(mocker):
    calls = []

    class MixedHook:
        @hook_impl
        def before_pipeline_run(self, run_params, pipeline, catalog):
            calls.append("pipeline")

        @hook_impl
        def before_node_run(self, node, catalog, inputs, is_async, session_id):
            calls.append("node")

    mocker.patch(
        "kedro_graphql.hooks.entry_points",
        return_value=[EntryPoint("mixed", MixedHook(), attr="mixed")],
    )

    local_manager = hook_manager_for(["mixed"], callbacks=LOCAL_HOOK_CALLBACKS)
    local_manager.hook.before_pipeline_run(run_params={}, pipeline=None, catalog=None)
    local_manager.hook.before_node_run(
        node=None, catalog=None, inputs={}, is_async=False, session_id="session"
    )

    assert calls == ["pipeline"]
    assert remote_hook_specs_for(["mixed"]) == [
        {
            "name": "mixed",
            "module": "tests.test_hooks",
            "attribute": "mixed",
            "callbacks": ["before_node_run"],
        }
    ]
