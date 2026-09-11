from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from kedro.framework.project import settings
from kedro.pipeline import Pipeline as KedroPipeline
from omegaconf import OmegaConf

from .config import KedroGraphQLConfig
from .models import PipelineTemplate


@dataclass(frozen=True)
class ProjectMetadata:
    pipelines: Mapping[str, KedroPipeline]
    config_sources: Mapping[str, Path]
    templates: tuple[PipelineTemplate, ...]


def _load_configuration(
    source: Path, config: KedroGraphQLConfig, globals: Mapping[str, Any] | None = None
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    loader = settings.CONFIG_LOADER_CLASS(
        conf_source=str(source), env=config.env, **settings.CONFIG_LOADER_ARGS
    )
    if globals:
        merged_globals = OmegaConf.to_container(
            OmegaConf.merge(loader["globals"], globals), resolve=True
        )
        loader._globals = merged_globals
        loader._globals_oc = None
    return loader["catalog"], loader["parameters"]


def load_pipeline_configuration(
    metadata: ProjectMetadata,
    config: KedroGraphQLConfig,
    name: str,
    globals: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Resolve one API pipeline's runtime-mounted Kedro configuration."""
    return _load_configuration(metadata.config_sources[name], config, globals)


def load_project_metadata(
    project_path: Path, config: KedroGraphQLConfig
) -> ProjectMetadata:
    """Load the project configuration needed by the API without a Kedro session."""

    from kedro.framework.project import pipelines

    if not config.pipeline_config_sources:
        raise ValueError("pipeline_config_sources must expose at least one pipeline")
    unknown = sorted(set(config.pipeline_config_sources) - set(pipelines))
    if unknown:
        raise ValueError(f"Unknown configured pipelines: {unknown}")
    empty_sources = sorted(
        name for name, source in config.pipeline_config_sources.items() if not source
    )
    if empty_sources:
        raise ValueError(f"Empty pipeline config sources: {empty_sources}")

    exposed = {name: pipelines[name] for name in config.pipeline_config_sources}
    sources = {
        name: source if source.is_absolute() else project_path / source
        for name, value in config.pipeline_config_sources.items()
        for source in (Path(value),)
    }
    templates = []
    for name, pipeline in sorted(exposed.items()):
        catalog, parameters = _load_configuration(sources[name], config)
        templates.append(
            PipelineTemplate(
                id=name,
                name=name,
                kedro_pipelines={name: pipeline},
                kedro_catalog=catalog,
                kedro_parameters=parameters,
            )
        )
    return ProjectMetadata(exposed, sources, tuple(templates))
