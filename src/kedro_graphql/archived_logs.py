"""Bounded reads of worker-owned execution attempt archives."""

import base64
import binascii
import json
import logging
import posixpath
from enum import Enum

import fsspec
import strawberry
from starlette.concurrency import run_in_threadpool

from .archive import _safe_segment
from .exceptions import InvalidPipeline
from .models import State
from .run_state import TERMINAL_STATES

logger = logging.getLogger(__name__)


@strawberry.enum
class ArchiveAvailability(Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNREADABLE = "UNREADABLE"


@strawberry.type
class ArchivedLogChunk:
    task_id: str | None
    availability: ArchiveAvailability
    message: str | None = None
    text: str = ""
    earlier_cursor: str | None = None
    skipped_content: bool = False


def _cursor(pipeline_id, task_id, offset):
    return base64.urlsafe_b64encode(json.dumps([pipeline_id, task_id, offset]).encode()).decode()


def _offset(before, pipeline_id, task_id):
    if before is None:
        return None
    try:
        if len(before) > 1024:
            raise ValueError()
        pipeline, task, offset = json.loads(base64.b64decode(before, altchars=b"-_", validate=True))
        if pipeline != pipeline_id or task != task_id or type(offset) is not int or offset < 0:
            raise ValueError()
        return offset
    except (ValueError, TypeError, binascii.Error, UnicodeError) as error:
        raise InvalidPipeline("Invalid archive cursor for the latest attempt.") from error


def _read_chunk(prefix, pipeline_id, task_id, before, max_bytes):
    fs, root = fsspec.core.url_to_fs(prefix)
    path = posixpath.join(root.rstrip("/"), "runs", _safe_segment(pipeline_id), _safe_segment(task_id), "events.jsonl")
    size = fs.size(path)
    end = size if before is None else before
    if end > size:
        raise InvalidPipeline("Archive changed; reload the latest logs.")
    start = max(0, end - max_bytes)
    with fs.open(path, "rb", block_size=max_bytes) as stream:
        stream.seek(start)
        raw = stream.read(end - start)
    skipped = False
    if start:
        boundary = raw.find(b"\n")
        if boundary >= 0:
            start += boundary + 1
            raw = raw[boundary + 1:]
        else:
            # shortcut: oversized records are skipped in bounded chunks; use a file download for full records.
            raw = b""
            skipped = True
    lines = []
    for line in raw.splitlines():
        try:
            decoded = line.decode("utf-8")
            if not isinstance(json.loads(decoded), dict):
                raise ValueError()
            lines.append(decoded)
        except (UnicodeError, ValueError):
            skipped = True
    return ArchivedLogChunk(
        task_id=task_id,
        availability=ArchiveAvailability.AVAILABLE,
        text="\n".join(lines),
        earlier_cursor=_cursor(pipeline_id, task_id, start) if start else None,
        skipped_content=skipped,
    )


async def pipeline_archived_logs(services, id, before=None, max_bytes=65536):
    if not 1 <= max_bytes <= 262144:
        raise InvalidPipeline("maxBytes must be between 1 and 262144.")
    pipeline = await services.backend.read(id=id)
    if pipeline is None:
        raise InvalidPipeline("Pipeline not found.")
    current = pipeline.current_status
    task_id = current.task_id
    offset = _offset(before, str(pipeline.id), task_id)
    if current.state not in TERMINAL_STATES.union({State.REVOKED}):
        return ArchivedLogChunk(task_id=task_id, availability=ArchiveAvailability.UNAVAILABLE,
                                message="Logs are archived after execution completes.")
    if not task_id or not services.config.log_path_prefix:
        return ArchivedLogChunk(task_id=task_id, availability=ArchiveAvailability.UNAVAILABLE,
                                message="Archived logs are unavailable for this attempt.")
    try:
        return await run_in_threadpool(_read_chunk, services.config.log_path_prefix,
                                      str(pipeline.id), task_id, offset, max_bytes)
    except FileNotFoundError:
        return ArchivedLogChunk(task_id=task_id, availability=ArchiveAvailability.UNAVAILABLE,
                                message="Archived logs are not available yet, or were not retained. You can retry.")
    except InvalidPipeline:
        raise
    except Exception:
        logger.warning("Unable to read archived logs pipeline_id=%s task_id=%s", id, task_id)
        return ArchivedLogChunk(task_id=task_id, availability=ArchiveAvailability.UNREADABLE,
                                message="Archived logs could not be read. You can retry.")


async def pipeline_log_download(services, info, id):
    """Sign the full latest-attempt archive without loading it into API memory."""
    from .models import DataSet
    from .signed_url.s3_provider import S3Provider
    from .signed_url.local_file_provider import LocalFileProvider

    pipeline = await services.backend.read(id=id)
    if pipeline is None:
        raise InvalidPipeline("Pipeline not found.")
    current = pipeline.current_status
    if current.state not in TERMINAL_STATES.union({State.REVOKED}):
        raise InvalidPipeline("Logs can be downloaded after execution completes.")
    prefix = services.config.log_path_prefix
    if not prefix or not current.task_id:
        raise InvalidPipeline("Archived logs are unavailable for this attempt.")
    pipeline_id, task_id = _safe_segment(str(pipeline.id)), _safe_segment(current.task_id)
    location = f"{prefix.rstrip('/')}/runs/{pipeline_id}/{task_id}/events.jsonl"
    expires = min(300, services.config.signed_url_max_expires_in_sec)
    try:
        if location.startswith("s3://"):
            signed = await run_in_threadpool(S3Provider.presigned_url, location, expires,
                f"{pipeline_id}-{task_id}.jsonl")
        else:
            dataset = DataSet(name="pipeline_logs", config=json.dumps({"type": "text.TextDataset", "filepath": location}))
            signed = await run_in_threadpool(LocalFileProvider.read, info, dataset, expires)
        if signed is None:
            raise FileNotFoundError()
        return signed
    except FileNotFoundError:
        raise InvalidPipeline("Archived logs are not available yet, or were not retained.") from None
