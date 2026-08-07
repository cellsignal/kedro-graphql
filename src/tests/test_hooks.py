import pytest
from kedro.framework.hooks import hook_impl

from kedro_graphql.hooks import hook_manager_for


class EntryPoint:
    def __init__(self, name, plugin):
        self.name = name
        self.plugin = plugin

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
