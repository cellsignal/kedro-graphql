from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from kedro.framework.project import settings
from kedro.pipeline import Pipeline as KedroPipeline

from .config import KedroGraphQLConfig
from .models import PipelineTemplate, PipelineTemplates


@dataclass(frozen=True)
class ProjectMetadata:
    pipelines: Mapping[str, KedroPipeline]
    catalog: Mapping[str, Any]
    parameters: Mapping[str, Any]
    templates: tuple[PipelineTemplate, ...]


def load_project_metadata(
    project_path: Path, config: KedroGraphQLConfig
) -> ProjectMetadata:
    """Load the project configuration needed by the API without a Kedro session."""

    conf_source = Path(config.conf_source or settings.CONF_SOURCE)
    if not conf_source.is_absolute():
        conf_source = project_path / conf_source
    loader = settings.CONFIG_LOADER_CLASS(
        conf_source=str(conf_source), env=config.env, **settings.CONFIG_LOADER_ARGS
    )
    from kedro.framework.project import pipelines

    catalog = loader["catalog"]
    parameters = loader["parameters"]
    templates = PipelineTemplates._build_pipeline_index(pipelines, catalog, parameters)
    return ProjectMetadata(pipelines, catalog, parameters, tuple(templates))
