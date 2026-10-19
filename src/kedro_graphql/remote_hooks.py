"""Load Kedro hooks in an external execution environment.

This module deliberately has no dependency on ``kedro_graphql`` so it can be
copied into an external runner image that only installs Kedro.
"""

import importlib
import logging
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from kedro.framework.hooks import _create_hook_manager

logger = logging.getLogger(__name__)

REMOTE_HOOK_CALLBACKS = (
    "before_node_run",
    "after_node_run",
    "on_node_error",
    "before_dataset_loaded",
    "after_dataset_loaded",
    "before_dataset_saved",
    "after_dataset_saved",
)
_REMOTE_HOOK_CALLBACKS = frozenset(REMOTE_HOOK_CALLBACKS)


class RemoteHookSpec(TypedDict):
    name: str
    module: str
    attribute: str
    callbacks: list[str]


class _FilteredHookPlugin:
    def __init__(self, plugin: Any, callbacks: Sequence[str], *, require: bool = False):
        for name, method in _filtered_hook_methods(plugin, callbacks, require=require):
            setattr(self, name, method)


def _hook_implementations(plugin: Any):
    for name in dir(plugin):
        method = getattr(plugin, name)
        marker = getattr(method, "kedro_impl", None)
        if marker is not None:
            yield marker.get("specname") or name, name, method


def _filtered_hook_methods(
    plugin: Any, callbacks: Sequence[str], *, require: bool
) -> list[tuple[str, Any]]:
    allowed = set(callbacks)
    found = set()
    methods = []
    for callback, name, method in _hook_implementations(plugin):
        if callback not in allowed:
            continue
        if not callable(method):
            if require:
                raise ValueError(
                    f"Remote hook callback {callback!r} is not callable"
                )
            continue
        found.add(callback)
        methods.append((name, method))

    if require:
        missing = sorted(allowed - found)
        if missing:
            raise ValueError(
                f"Remote hook plugin does not implement callbacks {missing}"
            )
    return methods


def hook_callbacks_for(plugin: Any, callbacks: Sequence[str]) -> list[str]:
    found = {
        callback
        for callback, _name, method in _hook_implementations(plugin)
        if callback in callbacks and callable(method)
    }
    return [callback for callback in callbacks if callback in found]


def filtered_hook_plugin(
    plugin: Any, callbacks: Sequence[str], *, require: bool = False
) -> Any:
    return _FilteredHookPlugin(plugin, callbacks, require=require)


def _dotted_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Remote hook spec field {field!r} must be a non-empty string")
    if any(not part.isidentifier() for part in value.split(".")):
        raise ValueError(f"Remote hook spec field {field!r} is not a dotted path")
    return value


def validate_remote_hook_spec(value: Any) -> RemoteHookSpec:
    if not isinstance(value, Mapping):
        raise TypeError("Remote hook specifications must be mappings")

    expected = {"name", "module", "attribute", "callbacks"}
    if set(value) != expected:
        raise ValueError(
            f"Remote hook specification must contain exactly {sorted(expected)}"
        )

    name = value["name"]
    if not isinstance(name, str) or not name:
        raise ValueError("Remote hook spec field 'name' must be a non-empty string")
    module = _dotted_path(value["module"], "module")
    attribute = _dotted_path(value["attribute"], "attribute")
    callbacks = value["callbacks"]
    if not isinstance(callbacks, list) or not callbacks:
        raise ValueError("Remote hook spec field 'callbacks' must be a non-empty list")
    if any(not isinstance(callback, str) for callback in callbacks):
        raise ValueError("Remote hook spec callbacks must be strings")
    if len(callbacks) != len(set(callbacks)):
        raise ValueError("Remote hook spec callbacks must not contain duplicates")
    if any(
        callback not in _REMOTE_HOOK_CALLBACKS
        for callback in callbacks
    ):
        raise ValueError("Remote hook spec contains an invalid callback")

    return {
        "name": name,
        "module": module,
        "attribute": attribute,
        "callbacks": callbacks,
    }


def _resolve_attribute(module: Any, attribute: str) -> Any:
    resolved = module
    for part in attribute.split("."):
        resolved = getattr(resolved, part)
    return resolved


def _is_missing_target_module(module: str, missing_name: str | None) -> bool:
    return bool(
        missing_name
        and (missing_name == module or module.startswith(f"{missing_name}."))
    )


def _target_module_available(module: str) -> bool:
    if module in sys.modules:
        return True
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError as error:
        if _is_missing_target_module(module, error.name):
            return False
        raise


def load_remote_hook_manager(specifications: list[Mapping[str, Any]]):
    """Build a Kedro hook manager from serialized external hook specs."""
    if not isinstance(specifications, list):
        raise TypeError("Remote hook specifications must be a list")

    manager = _create_hook_manager()
    names = set()
    for raw_spec in specifications:
        spec = validate_remote_hook_spec(raw_spec)
        if spec["name"] in names:
            raise ValueError(f"Duplicate remote hook name {spec['name']!r}")
        names.add(spec["name"])

        try:
            module = importlib.import_module(spec["module"])
        except ModuleNotFoundError as error:
            if _target_module_available(spec["module"]):
                raise
            if not _is_missing_target_module(spec["module"], error.name):
                raise
            logger.warning(
                "Skipping remote hook %s: module %s is not installed",
                spec["name"],
                spec["module"],
            )
            continue

        try:
            plugin = _resolve_attribute(module, spec["attribute"])
        except AttributeError:
            logger.warning(
                "Skipping remote hook %s: attribute %s.%s is not available",
                spec["name"],
                spec["module"],
                spec["attribute"],
            )
            continue

        filtered = filtered_hook_plugin(plugin, spec["callbacks"], require=True)
        manager.register(filtered, name=spec["name"])

    return manager
