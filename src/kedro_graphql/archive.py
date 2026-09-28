"""Worker-owned execution attempt archives."""

from __future__ import annotations

import json
import logging
import os
import posixpath
import shutil
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import fsspec

from .pipeline_config import _CREDENTIAL_FIELDS

logger = logging.getLogger(__name__)

_URL_SECRET_FIELDS = {
    "awsaccesskeyid",
    "credential",
    "signature",
    "sig",
    "x_amz_credential",
    "x_amz_security_token",
    "x_amz_signature",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_string(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value

    netloc = parsed.netloc
    if "@" in netloc:
        userinfo, host = netloc.rsplit("@", 1)
        if ":" in userinfo:
            username, _ = userinfo.split(":", 1)
            netloc = f"{username}:[REDACTED]@{host}"
        else:
            netloc = f"[REDACTED]@{host}"

    query = [
        (
            key,
            "[REDACTED]"
            if key.lower().replace("-", "_") in _CREDENTIAL_FIELDS
            or key.lower().replace("-", "_") in _URL_SECRET_FIELDS
            else item,
        )
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit(
        (parsed.scheme, netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def sanitize_config(value: Any, *, _key: str | None = None) -> Any:
    """Return JSON-safe configuration with credential-bearing values redacted."""
    if isinstance(value, Mapping):
        sanitized = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            sanitized[key] = (
                sanitize_config(item, _key=normalized)
                if normalized == "credentials" and isinstance(item, str)
                else "[REDACTED]"
                if normalized in _CREDENTIAL_FIELDS or normalized == "credentials"
                else sanitize_config(item, _key=normalized)
            )
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_config(item, _key=_key) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, Path, Enum)):
        return value.value if isinstance(value, Enum) else str(value)
    return str(value)


class PipelineTaskContextFilter(logging.Filter):
    """Add the execution identity to every task-scoped log record."""

    def __init__(self, pipeline_id: str, task_id: str):
        super().__init__()
        self.pipeline_id = pipeline_id
        self.task_id = task_id

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "pipeline_id", None) is None:
            record.pipeline_id = self.pipeline_id
        if getattr(record, "task_id", None) is None:
            record.task_id = self.task_id
        if getattr(record, "celery_task_id", None) is None:
            record.celery_task_id = self.task_id
        return True


def _safe_segment(value: str) -> str:
    value = str(value)
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"Invalid archive path segment: {value!r}")
    return value


class AttemptArchive:
    """Best-effort archive for one task using a local JSONL spool."""

    def __init__(
        self,
        prefix: str,
        pipeline_id: str,
        task_id: str,
        spool_dir: str | Path,
    ):
        self.failed = False
        self.failure: Exception | None = None
        self.manifest: dict[str, Any] = {}
        self.prefix = prefix
        self.pipeline_id = _safe_segment(pipeline_id)
        self.task_id = _safe_segment(task_id)
        self.spool_dir = Path(spool_dir)
        self.local_manifest_path = self.spool_dir / "manifest.json"
        self.local_events_path = self.spool_dir / "info.log"
        self.local_upload_events_path = self.spool_dir / "events-upload.jsonl"
        self._remote_ready = False
        self._spool_contains_prior_attempt = False

        try:
            self.spool_dir.mkdir(parents=True, exist_ok=True)
            self.local_events_path.touch(exist_ok=True)
            if self.local_manifest_path.exists():
                self._load_local_manifest()
                attempts = self.manifest.get("attempts", [])
                self._spool_contains_prior_attempt = bool(
                    attempts and attempts[-1].get("outcome") == "RETRY"
                )
        except Exception as error:
            self._fail(error)

        try:
            self._fs, root = fsspec.core.url_to_fs(prefix)
            self.directory = posixpath.join(
                root.rstrip("/"), "runs", self.pipeline_id, self.task_id
            )
            self.manifest_path = posixpath.join(self.directory, "manifest.json")
            self.events_path = posixpath.join(self.directory, "events.jsonl")
            if not self.manifest and self._fs.exists(self.manifest_path):
                self._load_remote_manifest()
            self._fs.makedirs(self.directory, exist_ok=True)
            self._remote_ready = True
        except Exception as error:
            self._fail(error)

    def _load_local_manifest(self) -> None:
        with self.local_manifest_path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        if isinstance(value, dict):
            self.manifest = value

    def _load_remote_manifest(self) -> None:
        with self._fs.open(self.manifest_path, "r", encoding="utf-8") as stream:
            value = json.load(stream)
        if isinstance(value, dict):
            self.manifest = value

    def _fail(self, error: Exception) -> None:
        first_failure = not self.failed
        self.failed = True
        self.failure = self.failure or error
        if first_failure:
            logger.error(
                "Attempt archive failed pipeline_id=%s task_id=%s: %s",
                self.pipeline_id,
                self.task_id,
                error,
            )

    def _write_local_manifest(self) -> bool:
        temporary_path = self.local_manifest_path.with_suffix(".json.tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as stream:
                json.dump(
                    sanitize_config(self.manifest),
                    stream,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                stream.write("\n")
            os.replace(temporary_path, self.local_manifest_path)
            return True
        except Exception as error:
            self._fail(error)
            return False

    def _upload(self, local_path: Path, remote_path: str) -> bool:
        try:
            self._fs.put(str(local_path), remote_path)
            return True
        except Exception as error:
            self._fail(error)
            return False

    def _prepare_events_upload(self) -> bool:
        try:
            with self.local_upload_events_path.open("w", encoding="utf-8") as stream:
                if not self._spool_contains_prior_attempt and self._fs.exists(self.events_path):
                    with self._fs.open(self.events_path, "r", encoding="utf-8") as previous:
                        shutil.copyfileobj(previous, stream)
                with self.local_events_path.open("r", encoding="utf-8") as current:
                    shutil.copyfileobj(current, stream)
            os.replace(self.local_upload_events_path, self.local_events_path)
            return True
        except Exception as error:
            self._fail(error)
            return False

    def start_attempt(self, manifest: Mapping[str, Any]) -> bool:
        """Write local state and publish the initial remote manifest."""
        current = sanitize_config(dict(manifest))
        attempts = list(self.manifest.get("attempts", []))
        attempt_number = len(attempts) + 1
        current["attempt"] = attempt_number
        current["attempts"] = attempts + [
            {
                "attempt": attempt_number,
                "started_at": current.get("started_at"),
                "outcome": None,
            }
        ]
        self.manifest = current
        if not self._write_local_manifest():
            return False
        if not self._remote_ready or self.failed:
            return False
        return self._upload(self.local_manifest_path, self.manifest_path)

    def update(self, **fields: Any) -> bool:
        self.manifest.update(sanitize_config(fields))
        return self._write_local_manifest()

    def write_manifest(self) -> bool:
        return self._write_local_manifest()

    def finalize(
        self,
        *,
        outcome: str,
        finished_at: str | None = None,
        worker_finished_at: str | None = None,
        error: str | None = None,
        traceback: str | None = None,
        celery_status: str | None = None,
    ) -> bool:
        try:
            worker_finished_at = worker_finished_at or utc_now()
            if finished_at is None and outcome != "ABORTING":
                finished_at = worker_finished_at
            self.manifest.update(
                {
                    "outcome": outcome,
                    "finished_at": finished_at,
                    "worker_finished_at": worker_finished_at,
                    "celery_status": celery_status,
                    "error": error,
                    "traceback": traceback,
                }
            )
            attempts = self.manifest.get("attempts", [])
            if attempts:
                attempts[-1].update(
                    {"finished_at": finished_at, "outcome": outcome, "error": error}
                )
            if not self._write_local_manifest():
                return False
            if not self._remote_ready or self.failed:
                return False
            if not self._prepare_events_upload():
                return False
            if not self._upload(self.local_events_path, self.events_path):
                return False
            return self._upload(self.local_manifest_path, self.manifest_path)
        except Exception as archive_error:
            self._fail(archive_error)
            return False
