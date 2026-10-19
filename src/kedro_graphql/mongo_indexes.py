"""Explicit Mongo index provisioning; index options belong to PyMongo."""

from pymongo import IndexModel


def index_models(config):
    """Validate all definitions before connecting, preserving compound key order."""
    collections = {}
    names = set()
    for position, definition in enumerate(config.mongo_indexes, start=1):
        options = dict(definition)
        collection = options.pop("collection", config.mongo_db_collection)
        keys = options.pop("keys", None)
        if not isinstance(collection, str) or not collection.strip():
            raise ValueError(f"mongo_indexes entry {position}: collection must be nonempty")
        if not isinstance(keys, list) or not keys or any(
            not isinstance(key, (list, tuple)) or len(key) != 2
            or not isinstance(key[0], str) or not key[0]
            for key in keys
        ):
            raise ValueError(f"mongo_indexes entry {position}: keys must be ordered field/direction pairs")
        try:
            model = IndexModel(keys, **options)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"mongo_indexes entry {position}: invalid PyMongo index definition") from exc
        if not isinstance(model.document["name"], str) or not model.document["name"]:
            raise ValueError(f"mongo_indexes entry {position}: index name must be nonempty")
        identity = (collection, model.document["name"])
        if identity in names:
            raise ValueError(f"mongo_indexes entry {position}: duplicate index name in collection")
        names.add(identity)
        collections.setdefault(collection, []).append(model)
    return collections
