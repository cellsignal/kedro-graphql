"""Explicit inspection and repair of optional catalog/tag search fields."""

from .catalog_search import build_dataset_search


def maintain_dataset_search(collection, rebuild=False):
    counts = {"checked": 0, "consistent": 0, "missing": 0, "unsupported": 0, "inconsistent": 0,
              "repaired": 0, "failed": 0}
    for original in collection.find({}, {"data_catalog": 1, "tags": 1, "dataset_search": 1}):
        counts["checked"] += 1
        document = original
        for attempt in range(3):
            catalog = document.get("data_catalog", [])
            try:
                expected = build_dataset_search(catalog, document.get("tags", []))
            except (ValueError, TypeError, KeyError, AttributeError):
                counts["failed"] += 1
                break
            actual = document.get("dataset_search")
            category = ("missing" if actual is None else "unsupported" if not isinstance(actual, dict) or actual.get("version") != 2
                        else "consistent" if actual == expected else "inconsistent")
            if attempt == 0:
                counts[category] += 1
            if not rebuild or actual == expected:
                break
            query = {"_id": document["_id"], "data_catalog": catalog} if "data_catalog" in document else {
                "_id": document["_id"], "data_catalog": {"$exists": False}}
            query["tags"] = document["tags"] if "tags" in document else {"$exists": False}
            result = collection.update_one(query, {"$set": {"dataset_search": expected}})
            if result.matched_count:
                counts["repaired"] += 1
                break
            document = collection.find_one({"_id": document["_id"]}, {"data_catalog": 1, "tags": 1, "dataset_search": 1})
            if document is None or attempt == 2:
                counts["failed"] += 1
                break
    return counts
