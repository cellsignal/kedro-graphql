"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
from kedro_graphql.viz.components.template import KedroGraphqlMaterialTemplate
from kedro_graphql.viz.components.pipeline_cards import PipelineCards
from kedro_graphql.viz.components.pipeline_search import PipelineSearch
from kedro_graphql.viz.components.pipeline_monitor import PipelineMonitor
from kedro_graphql.viz.components.pipeline_form_factory import PipelineFormFactory
from kedro_graphql.viz.components.pipeline_data_factory import PipelineDataFactory
from kedro_graphql.viz.decorators import discover_plugins
from kedro_graphql.config import config


def pipeline_cards():
    template = KedroGraphqlMaterialTemplate()
    template.main.append(PipelineCards())
    return template

def pipeline_search():
    template = KedroGraphqlMaterialTemplate()
    template.main.append(PipelineSearch())
    return template

def pipeline_monitor():
    template = KedroGraphqlMaterialTemplate()
    template.main.append(PipelineMonitor())
    return template

def pipeline_forms():
    template = KedroGraphqlMaterialTemplate()
    p = PipelineFormFactory()
    template.main.append(p)
    return template

def pipeline_data():
    template = KedroGraphqlMaterialTemplate()
    p = PipelineDataFactory()
    template.main.append(p)
    return template




def app_factory():
    return {
       config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + '/cards': pipeline_cards,
       config["KEDRO_GRAPHQL_VIZ_BASEPATH"] +'/search': pipeline_search,
       config["KEDRO_GRAPHQL_VIZ_BASEPATH"] +'/monitor': pipeline_monitor,
       config["KEDRO_GRAPHQL_VIZ_BASEPATH"] +'/form': pipeline_forms,
       config["KEDRO_GRAPHQL_VIZ_BASEPATH"] +'/data': pipeline_data
    }


def start_viz():
    #pn.config.reuse_sessions = True
    pn.config.admin = True
    #pn.config.global_loading_spinner = True

    discover_plugins(config)
    pn.serve(app_factory(), admin = True, port=5006)