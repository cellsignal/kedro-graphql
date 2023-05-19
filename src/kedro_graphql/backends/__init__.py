from kedro_graphql.config import config
from importlib import import_module

def init_backend():
    backend_module, backend_class = config["KEDRO_GRAPHQL_BACKEND"].rsplit(".", 1)
    backend_kwargs = {"uri": config.get("MONGO_URI"), "db": config.get("MONGO_DB_NAME")}
    backend_module = import_module(backend_module)
    backend = getattr(backend_module, backend_class)
    return backend(**backend_kwargs)