"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
from kedro_graphql.viz.components.template import KedroGraphqlMaterialTemplate
from kedro_graphql.viz.components.pipeline_cards import PipelineCards
from kedro_graphql.viz.components.pipeline_search import PipelineSearch
from kedro_graphql.viz.components.pipeline_monitor import PipelineMonitor
from kedro_graphql.viz.decorators import discover_plugins, VIZ_PLUGINS
from kedro_graphql.logs.logger import logger
from kedro_graphql.config import config

def pipeline_cards():
    template = KedroGraphqlMaterialTemplate().__panel__()
    template.main.append(PipelineCards())
    return template

def pipeline_search():
    template = KedroGraphqlMaterialTemplate().__panel__()
    template.main.append(PipelineSearch())
    return template

def pipeline_monitor():
    template = KedroGraphqlMaterialTemplate().__panel__()
    template.main.append(PipelineMonitor())
    return template

apps = {
    '/pipelines/cards': pipeline_cards,
    '/pipelines/search': pipeline_search,
    '/pipelines/monitor': pipeline_monitor
}

def build_pipeline_form(form, pipeline_name = None):
   template = KedroGraphqlMaterialTemplate().__panel__()
   template.main.append(form(pipeline_name = pipeline_name, monitor_pathname = "/pipelines/monitor")) 
   return template

def discover_apps(apps):
    discover_plugins(config)
    for k,v in VIZ_PLUGINS["FORMS"].items():
            for f in v:
                apps["pipelines/forms/"+ k + "/" + f.__name__] = build_pipeline_form(f, k)
    return apps

if __name__ == "__main__":
    apps = discover_apps(apps)
    pn.serve(apps, port=5006)