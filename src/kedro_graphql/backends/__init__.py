from importlib import import_module

from ..config import KedroGraphQLConfig


def init_backend(config: KedroGraphQLConfig):
    backend_module, backend_class = config.backend.rsplit(".", 1)
    backend_kwargs = {
        "uri": config.mongo_uri,
        "db": config.mongo_db_name,
        "collection": config.mongo_db_collection,
    }
    backend_module = import_module(backend_module)
    backend = getattr(backend_module, backend_class)
    return backend(**backend_kwargs)
