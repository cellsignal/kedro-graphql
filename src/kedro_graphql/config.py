from kedro.framework.startup import bootstrap_project
from kedro.framework.session import KedroSession
from kedro.framework.project import pipelines as PIPELINES
from pathlib import Path
from dotenv import dotenv_values
import os
from importlib import import_module

## pyproject.toml located in parent directory, required for project config
project_path = Path.cwd()
metadata = bootstrap_project(project_path)
session = KedroSession.create(metadata.package_name, project_path=project_path)
context = session.load_context()

conf_catalog = context.config_loader["catalog"]
conf_parameters = context.config_loader["parameters"]

## define defaults
config = {
    "MONGO_URI": "mongodb://root:example@localhost:27017/",
    "MONGO_DB_NAME": "pipelines",
    "KEDRO_GRAPHQL_IMPORTS": "kedro_graphql.plugins.plugins,",
    "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphql"
    }

load_config = {
    **dotenv_values(".env"),  # load 
    **os.environ,  # override loaded values with environment variables
}

## override defaults
config.update(load_config)

## parse imports
#config["KEDRO_GRAPHQL_IMPORTS"] = [i.strip() for i in config["KEDRO_GRAPHQL_IMPORTS"].split(",") if len(i.strip()) > 0]
imports = [i.strip() for i in config["KEDRO_GRAPHQL_IMPORTS"].split(",") if len(i.strip()) > 0]

## ".backends.mongodb.MongoBackend"
backend_module, backend_class = "kedro_graphql.backends.mongodb.MongoBackend".rsplit(".", 1)
backend_kwargs = {"uri": config.get("MONGO_URI"), "db": config.get("MONGO_DB_NAME")}
backend_module = import_module(backend_module)
backend = getattr(backend_module, backend_class)

RESOLVER_PLUGINS = {}
TYPE_PLUGINS = {"query":[],
                "mutation":[],
                "subscription":[]}

## discover plugins e.g. decorated functions e.g @gql_resolver, @gql_query, etc...
#for i in config["KEDRO_GRAPHQL_IMPORTS"]:
for i in imports:
    import_module(i)