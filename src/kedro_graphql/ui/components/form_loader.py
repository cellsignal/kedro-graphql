import importlib

def form_loader(pipeline_template = {}):
    mod = importlib.import_module(f"kedro_graphql.ui.components.forms.{pipeline_template['name']}.{pipeline_template['name']}")
    return mod.load(pipeline_template)