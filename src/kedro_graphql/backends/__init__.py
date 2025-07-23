from importlib import import_module


def init_backend(config):
    backend_module, backend_class = config["KEDRO_GRAPHQL_BACKEND"].rsplit(".", 1)
    backend_kwargs = {"uri": config.get("KEDRO_GRAPHQL_MONGO_URI"), "db": config.get(
        "KEDRO_GRAPHQL_MONGO_DB_NAME"), "collection": config.get("KEDRO_GRAPHQL_MONGO_DB_COLLECTION")}
    backend_module = import_module(backend_module)
    backend = getattr(backend_module, backend_class)
    return backend(**backend_kwargs)
