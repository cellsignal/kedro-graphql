"""Pipeline name policy for submission choices and search results."""

import json

from .config import KedroGraphQLConfig
from .exceptions import InvalidPipeline


def pipeline_name_allowed(config: KedroGraphQLConfig, name: str) -> bool:
    return (
        (config.pipeline_name_allowlist is None or name in config.pipeline_name_allowlist)
        and name not in config.pipeline_name_disallowlist
    )


def require_pipeline_name_allowed(config: KedroGraphQLConfig, name: str) -> None:
    if not pipeline_name_allowed(config, name):
        raise InvalidPipeline(f"Pipeline {name} is not available for submission.")


def pipeline_search_filter(config: KedroGraphQLConfig, filter: str | None) -> str | None:
    """Apply the name policy before pagination without replacing caller filters."""
    names = {}
    if config.pipeline_name_allowlist is not None:
        names["$in"] = config.pipeline_name_allowlist
    if config.pipeline_name_disallowlist:
        names["$nin"] = config.pipeline_name_disallowlist
    if not names:
        return filter
    query = json.loads(filter) if filter else {}
    if not isinstance(query, dict):
        raise ValueError("Filter must be a JSON object")
    restriction = {"name": names}
    return json.dumps({"$and": [query, restriction]} if query else restriction)


def pipeline_submission_name_allowed(config: KedroGraphQLConfig, name: str) -> bool:
    return pipeline_name_allowed(config, name) and (
        config.pipeline_submission_name_allowlist is None
        or name in config.pipeline_submission_name_allowlist
    )


def require_pipeline_submission_name_allowed(config: KedroGraphQLConfig, name: str) -> None:
    if not pipeline_submission_name_allowed(config, name):
        raise InvalidPipeline(f"Pipeline {name} is not available for generic submission.")
