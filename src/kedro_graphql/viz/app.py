"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
from panel.io.location import Location
from kedro_graphql.viz.components.template import KedroGraphqlMaterialTemplate
from kedro_graphql.viz.components.pipeline_cards import PipelineCards
from kedro_graphql.viz.components.pipeline_search import PipelineSearch
from kedro_graphql.viz.components.pipeline_monitor import PipelineMonitor
from kedro_graphql.viz.components.pipeline_detail import PipelineDetail
from kedro_graphql.viz.decorators import discover_plugins, VIZ_PLUGINS
from kedro_graphql.logs.logger import logger
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

def app_factory():
    return {
        '/pipelines/cards': pipeline_cards,
        '/pipelines/search': pipeline_search,
        '/pipelines/monitor': pipeline_monitor
    }

##def build_form_plugin(form, name = None):
##   template = KedroGraphqlMaterialTemplate()
##   template.main.append(form(name = name, form = form.__name__)) 
##   return template

def build_data_plugin(plugin, pipeline_name = "", pipeline_id = ""):
   template = KedroGraphqlMaterialTemplate()
   tabs = pn.Tabs(dynamic=False)

   ## append data catalog tab first
   catalog = PipelineDetail()
   tabs.append(("Data Catalog", catalog))
   for p in plugin:
       ## lets remove these args and just use the pn.stat.locaiton.sync(self, {"id":"id"}) approach in the plugins
       p_instance = p(pipeline_name = pipeline_name, pipeline_id = pipeline_id)
       tabs.append((p_instance.display_name, p))
   template.main.append(tabs) 
   return template


def discover_apps(apps):
    discover_plugins(config)
    for k,v in VIZ_PLUGINS["FORMS"].items():
        for form in v:
            logger.info("discovered form plugin: " + form.__name__)
            #apps["pipelines/forms/"+ k + "/" + form.__name__] = build_form_plugin(form, k)
            apps["pipelines/forms/"+ k + "/" + form.__name__] = form
            logger.info("built form plugin: /pipelines/forms/"+k + "/" + form.__name__)
    
    for k,v in VIZ_PLUGINS["DATA"].items():
        #apps["pipelines/data/"+k] = build_data_plugin(v, pipeline_name = k)
        apps["pipelines/data/"+k] = v
    return apps

def start_viz():
    #pn.config.reuse_sessions = True
    pn.config.admin = True
    #pn.config.global_loading_spinner = True


    apps = discover_apps(app_factory())
    #apps.servable()
    pn.serve(apps, admin = True, port=5006)