"""Application-supplied search providers for dataset input values."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Mapping

import strawberry
from strawberry.scalars import JSON
from starlette.concurrency import run_in_threadpool

from .exceptions import InvalidPipeline


@dataclass(frozen=True)
class DatasetInputContext:
    pipeline_name: str
    dataset_name: str
    catalog_config: Mapping[str, Any]
    slices: tuple
    caller: Mapping[str, Any] | None


@strawberry.type
class InputAutocomplete:
    method: str


@strawberry.type
class InputSuggestion:
    label: str
    value: JSON


@strawberry.type
class InputSuggestions:
    items: list[InputSuggestion]
    truncated: bool = False


class DatasetInputProvider(ABC):
    """Eligibility must be local and cheap; search may perform blocking I/O.

    Providers enforce their own data scope and caller-specific access. Returned
    values use the existing input representation identified by ``method``.
    """
    method: str

    @abstractmethod
    def supports(self, context: DatasetInputContext) -> bool:
        ...

    def resolve(self, context: DatasetInputContext, value: str) -> str:
        """Resolve an application input value before standard location validation."""
        return value

    @abstractmethod
    def search(self, context: DatasetInputContext, query: str, limit: int) -> InputSuggestions:
        ...


@dataclass(frozen=True)
class InputProviderBinding:
    pipeline_name: str
    dataset_name: str
    provider: DatasetInputProvider


def load_input_providers(registrations):
    providers = []
    for registration in registrations:
        module, name = registration.provider.rsplit(".", 1)
        cls = getattr(import_module(module), name)
        if not issubclass(cls, DatasetInputProvider):
            raise TypeError(f"{registration.provider} must inherit from DatasetInputProvider")
        provider = cls(**registration.options)
        if not isinstance(provider.method, str) or not provider.method:
            raise ValueError(f"{registration.provider} must identify its input method")
        providers.append(InputProviderBinding(registration.pipeline_name, registration.dataset_name, provider))
    return tuple(providers)


def find_input_provider(services, context, methods):
    matches = [binding.provider for binding in services.input_providers
               if binding.pipeline_name == context.pipeline_name
               and binding.dataset_name == context.dataset_name
               and binding.provider.method in methods
               and binding.provider.supports(context)]
    if len(matches) > 1:
        raise InvalidPipeline(f"Multiple autocomplete providers match input {context.dataset_name}")
    return matches[0] if matches else None


async def dataset_input_suggestions(services, name, dataset_name, slices, query, limit, caller):
    from .pipeline_submission import _form_context, build_submission_form

    if not 1 <= limit <= 50:
        raise InvalidPipeline("Suggestion limit must be between 1 and 50.")
    if len(query) > 1024:
        raise InvalidPipeline("Suggestion search text is too long.")
    form = build_submission_form(services, name, slices)
    descriptor = next((item for item in form.inputs if item.name == dataset_name), None)
    if descriptor is None or not descriptor.supported:
        raise InvalidPipeline("Dataset is not a supported free input in the selected graph.")
    _, catalog, resolved, _ = _form_context(services, name, slices)
    context = DatasetInputContext(name, dataset_name, resolved.get(dataset_name) or catalog.get(dataset_name) or {}, tuple(slices or []), caller)
    provider = find_input_provider(services, context, [method.value for method in descriptor.methods])
    if provider is None:
        raise InvalidPipeline("Autocomplete is not configured for this dataset input.")
    query = query.strip()
    if len(query) < 2:
        return InputSuggestions(items=[])
    result = await run_in_threadpool(provider.search, context, query, limit)
    if not isinstance(result, InputSuggestions):
        raise TypeError("Dataset input provider must return InputSuggestions")
    return InputSuggestions(items=result.items[:limit], truncated=result.truncated or len(result.items) > limit)
