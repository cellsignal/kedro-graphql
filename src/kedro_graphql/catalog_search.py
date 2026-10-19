"""Shared tag/location matching and atomic catalog search projection."""

import asyncio
import base64
import bisect
import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import strawberry
from bson import ObjectId
from pymongo.errors import ExecutionTimeout

from .logs.logger import logger
from .models import DataSet, PageMeta, Pipeline, Pipelines, _decode_datetime
from .pipeline_visibility import pipeline_search_filter


@strawberry.input
class CatalogSearchInput:
    text: str = ""
    pipeline_id: str | None = None
    dataset_name: str | None = None
    pipeline_name: str | None = None


@strawberry.type
class DatasetSearchRow:
    dataset: DataSet
    pipeline_id: str
    pipeline_name: str
    catalog_index: int


@strawberry.type
class DatasetSearchResults:
    datasets: list[DatasetSearchRow]
    page_meta: PageMeta


@dataclass
class CatalogSearchResults:
    pipelines: Pipelines
    datasets: DatasetSearchResults


def search_entry(dataset, index, strict=True):
    try:
        config = json.loads(dataset["config"])
        if not isinstance(config, dict):
            raise ValueError("Dataset configuration must be an object")
    except (ValueError, TypeError, KeyError):
        if strict:
            raise
        config = {}
    kind = config.get("type", "")
    kind = kind if isinstance(kind, str) else ""
    locations = [config.get("filepath"), config.get("path")]
    if isinstance(config.get("paths"), list):
        locations.extend(config["paths"])
    return {
        "catalog_index": index,
        "name_folded": dataset["name"].casefold(),
        "type_folded": kind.casefold(),
        "type_short_folded": kind.rsplit(".", 1)[-1].casefold(),
        "locations_folded": sorted({value.casefold() for value in locations if isinstance(value, str) and value}),
    }


def build_dataset_search(catalog, tags=()):
    return {"version": 2, "datasets": [search_entry(dataset, index) for index, dataset in enumerate(catalog)],
            "pipeline_tags": [{"key": tag["key"], "value_folded": tag["value"].casefold()} for tag in tags]}


def build_pipeline_document(pipeline: Pipeline):
    """Serialize the authoritative catalog, tags, and their projection together."""
    values = pipeline.to_dict()
    try:
        values["dataset_search"] = build_dataset_search(values.get("data_catalog", []), values.get("tags", []))
    except (ValueError, TypeError, KeyError, AttributeError):
        logger.warning("Dataset search enrichment failed for pipeline %s; saving without enrichment", pipeline.id)
    return values


def pipeline_document_update(values):
    update = {"$set": values}
    if "dataset_search" not in values:
        update["$unset"] = {"dataset_search": ""}
    return update


def public_pipeline_document(values):
    values = dict(values)
    values.pop("dataset_search", None)
    return values


def mask_dataset(dataset, masks):
    result = dict(dataset)
    try:
        config = json.loads(result["config"])
        if not isinstance(config, dict):
            return result
        def mask(value):
            for rule in masks:
                if value.startswith(rule["prefix"]):
                    value = rule["mask"] + value[len(rule["prefix"]):]
            return value
        for key in ("filepath", "path"):
            if isinstance(config.get(key), str):
                config[key] = mask(config[key])
        if isinstance(config.get("paths"), list):
            config["paths"] = [mask(value) if isinstance(value, str) else value for value in config["paths"]]
        result["config"] = json.dumps(config)
    except (ValueError, TypeError):
        pass
    return result


def expanded_terms(text, config):
    values = [text]
    if config.catalog_search_term_expander:
        module, name = config.catalog_search_term_expander.rsplit(".", 1)
        extra = getattr(importlib.import_module(module), name)(text)
        if not isinstance(extra, (list, tuple)) or any(not isinstance(value, str) for value in extra):
            raise ValueError("Search term expansion must return a list of strings.")
        values.extend(extra)
    terms = sorted({value.strip().casefold() for value in values if value.strip()})
    if len(terms) > 20 or any(len(value) > 1024 for value in terms):
        raise ValueError("Search term expansion exceeds the allowed size.")
    return terms


def decode_cursor(cursor, fingerprint, size):
    if not cursor:
        return None
    try:
        payload = json.loads(base64.b64decode(cursor, validate=True))
        key = payload["key"]
        if payload["query"] != fingerprint or not isinstance(key, list) or len(key) != size:
            raise ValueError()
        if not all(isinstance(value, str) for value in key[:2]) or not ObjectId.is_valid(key[1]):
            raise ValueError()
        if size == 2 and (len(key[0]) != 20 or not key[0].isascii() or not key[0].isdigit()):
            raise ValueError()
        if size == 3 and (type(key[2]) is not int or key[2] < 0):
            raise ValueError()
        return tuple(key)
    except (ValueError, TypeError, KeyError):
        raise ValueError("Invalid catalog search cursor; restart the search.") from None


async def search_catalog(services, search, pipeline_limit=10, dataset_limit=50,
                         pipeline_cursor=None, dataset_cursor=None, *, connection=None):
    if not all(1 <= limit <= 200 for limit in (pipeline_limit, dataset_limit)):
        raise ValueError("Search limits must be between 1 and 200.")
    text = search.text.strip()
    pipeline_name = (search.pipeline_name or "").strip()
    if len(pipeline_name) > 256:
        raise ValueError("Pipeline name must be at most 256 characters.")
    if len(text) > 1024 or (len(text) < 3 and not search.pipeline_id and not pipeline_name):
        raise ValueError("Enter at least three characters or an exact pipeline ID.")
    config = services.config
    terms = expanded_terms(text, config)
    name_filter = (search.dataset_name or "").strip().casefold()
    if len(name_filter) > 1024:
        raise ValueError("Dataset name filter must be at most 1024 characters.")
    keys = config.catalog_search_tag_keys
    identity = {"terms": terms, "id": search.pipeline_id, "dataset_name": name_filter, "pipeline_name": pipeline_name,
                "keys": keys, "allow": config.pipeline_name_allowlist,
                "disallow": config.pipeline_name_disallowlist, "masks": config.dataset_filepath_masks}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    pipeline_after = decode_cursor(pipeline_cursor, fingerprint + "pipelines", 2)
    dataset_after = decode_cursor(dataset_cursor, fingerprint + "datasets", 3)
    scope = json.loads(pipeline_search_filter(config, "{}"))
    if pipeline_name:
        scope = {"$and": [scope, {"name": pipeline_name}]}
    if search.pipeline_id:
        if not ObjectId.is_valid(search.pipeline_id):
            raise ValueError("Pipeline ID must be a valid Mongo object ID.")
        scope = {"$and": [scope, {"_id": ObjectId(search.pipeline_id)}]}
    expressions = [{"$regex": re.escape(term)} for term in terms]
    tag_conditions = [{"value_folded": expression} for expression in expressions]
    if keys is not None:
        tag_conditions = [{**condition, "key": {"$in": keys}} for condition in tag_conditions]
    matches = ([{"dataset_search.pipeline_tags": {"$elemMatch": condition}} for condition in tag_conditions]
               + [{"dataset_search.datasets.locations_folded": expression} for expression in expressions])
    collection = services.backend._get_collection()
    timeout = config.dataset_search_timeout_seconds
    pipelines, datasets = [], []

    def retain(rows, key, value, after, limit):
        if after is not None and key <= after:
            return
        bisect.insort(rows, (key, value), key=lambda row: row[0])
        if len(rows) > limit + 1:
            rows.pop()

    try:
        async with asyncio.timeout(timeout):
            queries = [
                ({"$and": [scope, {"dataset_search.version": 2}, {"$or": matches} if terms else {}]},
                 {"name": 1, "created_at": 1, "tags": 1, "dataset_search": 1}),
                ({"$and": [scope, {"dataset_search.version": {"$ne": 2}}]},
                 {"name": 1, "created_at": 1, "tags": 1, "dataset_search": 1, "data_catalog": 1}),
            ]
            for query, projection_fields in queries:
                cursor = collection.find(query, projection_fields).max_time_ms(int(timeout * 1000))
                try:
                    async for document in cursor:
                        projection = document.get("dataset_search")
                        if not isinstance(projection, dict) or projection.get("version") != 2:
                            entries = []
                            for index, item in enumerate(document.get("data_catalog", [])):
                                entries.append(search_entry(item, index, strict=False))
                                if index % 128 == 0:
                                    await asyncio.sleep(0)
                            projection = {"datasets": entries,
                                          "pipeline_tags": [{"key": tag.get("key"), "value_folded": str(tag.get("value", "")).casefold()}
                                                            for tag in document.get("tags", [])]}
                        tag_match = not terms or any(
                            (keys is None or tag["key"] in keys) and any(term in tag["value_folded"] for term in terms)
                            for tag in projection["pipeline_tags"])
                        location_match = tag_match or any(
                            term in location for entry in projection["datasets"]
                            for term in terms for location in entry["locations_folded"])
                        if not location_match:
                            continue
                        matching = (entry for entry in projection["datasets"] if tag_match or any(
                            term in location for term in terms for location in entry["locations_folded"]))
                        created = _decode_datetime(document.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
                        # Fixed-width reverse date and ID give descending pipeline order with ascending cursors.
                        stamp = created.strftime("%Y%m%d%H%M%S%f").zfill(20)
                        pipeline_key = ("".join(str(9-int(char)) for char in stamp),
                                        f"{(1 << 96)-1-int(str(document['_id']),16):024x}")
                        if connection != "datasets":
                            retain(pipelines, pipeline_key, document, pipeline_after, pipeline_limit)
                        for offset, entry in enumerate(matching if connection != "pipelines" else []):
                            if offset % 128 == 0:
                                await asyncio.sleep(0)
                            if name_filter and name_filter not in entry["name_folded"]:
                                continue
                            key = (entry["name_folded"], str(document["_id"]), entry["catalog_index"])
                            retain(datasets, key, (document, entry["catalog_index"]), dataset_after, dataset_limit)
                        await asyncio.sleep(0)
                finally:
                    await cursor.close()
            selected_ids = {document["_id"] for _, document in pipelines}
            selected_ids.update(document["_id"] for _, (document, _) in datasets)
            full_documents = {}
            if selected_ids:
                cursor = collection.find({"$and": [scope, {"_id": {"$in": list(selected_ids)}}]}).max_time_ms(int(timeout * 1000))
                try:
                    async for document in cursor:
                        full_documents[document["_id"]] = document
                finally:
                    await cursor.close()
            candidates_by_id = {document["_id"]: document for _, document in pipelines}
            candidates_by_id.update({document["_id"]: document for _, (document, _) in datasets})
            for identity, candidate in candidates_by_id.items():
                full = full_documents.get(identity)
                source_fields = ("name", "created_at", "tags", "dataset_search")
                if "data_catalog" in candidate:
                    source_fields += ("data_catalog",)
                if full is None or any(full.get(field) != candidate.get(field) for field in source_fields):
                    raise ValueError("Catalog changed during search; please retry.")
    except (TimeoutError, ExecutionTimeout):
        raise ValueError("Catalog search timed out. Narrow the text or specify a pipeline ID.") from None

    def page(rows, limit, connection):
        next_cursor = None
        if len(rows) > limit:
            rows.pop()
            next_cursor = base64.b64encode(json.dumps({"query": fingerprint + connection, "key": rows[-1][0]}).encode()).decode()
        return PageMeta(next_cursor=next_cursor)

    pipeline_meta = page(pipelines, pipeline_limit, "pipelines")
    dataset_meta = page(datasets, dataset_limit, "datasets")
    public = []
    for _, document in pipelines:
        values = public_pipeline_document(full_documents[document["_id"]])
        values["id"] = str(values.pop("_id"))
        values["data_catalog"] = [mask_dataset(item, config.dataset_filepath_masks) for item in values.get("data_catalog", [])]
        public.append(Pipeline.from_dict(values))
    rows = [DatasetSearchRow(dataset=DataSet.from_dict(mask_dataset(full_documents[document["_id"]]["data_catalog"][index], config.dataset_filepath_masks)),
                             pipeline_id=str(document["_id"]), pipeline_name=document["name"], catalog_index=index)
            for _, (document, index) in datasets]
    return CatalogSearchResults(pipelines=Pipelines(pipelines=public, page_meta=pipeline_meta),
                                datasets=DatasetSearchResults(datasets=rows, page_meta=dataset_meta))
