from importlib.metadata import entry_points
from typing import Any

from kedro.framework.hooks import _create_hook_manager, hook_impl
from kedro.io import CatalogProtocol
from kedro.pipeline import Pipeline

from .exceptions import InvalidPipeline
from .remote_hooks import (
    REMOTE_HOOK_CALLBACKS,
    RemoteHookSpec,
    filtered_hook_plugin,
    hook_callbacks_for,
    validate_remote_hook_spec,
)

LOCAL_HOOK_CALLBACKS = (
    "after_catalog_created",
    "before_pipeline_run",
    "after_pipeline_run",
    "on_pipeline_error",
)


def available_hook_names() -> set[str]:
    """Return the installed Kedro hook entry-point names."""
    return set(_entry_points_by_name())


def _entry_points_by_name():
    selected = list(entry_points(group="kedro.hooks"))
    names = [entry_point.name for entry_point in selected]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ValueError(f"Duplicate Kedro hook entry points: {sorted(duplicates)}")
    return {entry_point.name: entry_point for entry_point in selected}


def _selected_plugins(hook_names: list[str]):
    entry_points_by_name = _entry_points_by_name()
    missing = sorted(set(hook_names) - entry_points_by_name.keys())
    if missing:
        raise ValueError(f"Unavailable Kedro hooks: {missing}")

    plugins = []
    for name in dict.fromkeys(hook_names):
        entry_point = entry_points_by_name[name]
        plugin = entry_point.load()
        if any(plugin is registered for registered in plugins):
            raise ValueError(f"Kedro hook {name!r} resolves to a duplicate plugin")
        plugins.append(plugin)
        yield name, entry_point, plugin


def hook_manager_for(hook_names: list[str], callbacks=None):
    """Build a Kedro hook manager containing exactly ``hook_names``."""
    manager = _create_hook_manager()
    for name, _entry_point, plugin in _selected_plugins(hook_names):
        manager.register(
            plugin if callbacks is None else filtered_hook_plugin(plugin, callbacks),
            name=name,
        )
    return manager


def remote_hook_specs_for(hook_names: list[str]) -> list[RemoteHookSpec]:
    specs = []
    for name, entry_point, plugin in _selected_plugins(hook_names):
        callbacks = hook_callbacks_for(plugin, REMOTE_HOOK_CALLBACKS)
        if not callbacks:
            continue
        specs.append(
            validate_remote_hook_spec(
                {
                    "name": name,
                    "module": entry_point.module,
                    "attribute": entry_point.attr,
                    "callbacks": callbacks,
                }
            )
        )
    return specs


class DataValidationHooks:
    """
    A Kedro hook class to validate the existence of input datasets before running a pipeline.
    """

    @hook_impl
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol
    ) -> None:
        """Hook to be invoked before a pipeline runs.

        Args:
            run_params: The params used to run the pipeline.
            pipeline: The ``Pipeline`` that will be run.
            catalog: An implemented instance of ``CatalogProtocol`` to be used during the run.
        """

        # Only check the free inputs (excluding parameters) for validation
        filtered_keys = [key for key in pipeline.inputs(
        ) if not key.startswith('params:') and key != 'parameters']

        # Check to see if all free inputs exist
        for input in filtered_keys:
            if not catalog.exists(input):
                raise InvalidPipeline(f"Input dataset {input} does not exist.")


validation_hooks = DataValidationHooks()
