import json
from pathlib import Path

import fsspec

from kedro_graphql.archive import AttemptArchive, sanitize_config


def _remote_json(fs, path):
    with fs.open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def test_attempt_archive_uploads_local_jsonl_spool_and_snapshots(tmp_path):
    spool = tmp_path / "task"
    spool.mkdir()
    (spool / "info.log").write_text('{"message":"node ran"}\n', encoding="utf-8")
    archive = AttemptArchive("memory://archive", "pipeline-id", "task-id", spool)

    assert archive.start_attempt(
        {
            "pipeline_id": "pipeline-id",
            "task_id": "task-id",
            "configuration": {
                "parameters": {
                    "password": "secret",
                    "credentials": "aws-prod",
                    "url": "s3://user:secret@bucket/key?X-Amz-Signature=secret&keep=yes",
                }
            },
            "started_at": "2026-09-28T14:00:00+00:00",
        }
    )
    assert archive.finalize(
        outcome="SUCCESS",
        finished_at="2026-09-28T14:01:00+00:00",
        worker_finished_at="2026-09-28T14:01:01+00:00",
        celery_status="SUCCESS",
    )

    fs, root = fsspec.core.url_to_fs("memory://archive")
    remote = Path(root) / "runs" / "pipeline-id" / "task-id"
    manifest = _remote_json(fs, str(remote / "manifest.json"))
    with fs.open(str(remote / "events.jsonl"), "r", encoding="utf-8") as stream:
        events = stream.read()

    assert manifest["outcome"] == "SUCCESS"
    assert manifest["finished_at"] == "2026-09-28T14:01:00+00:00"
    assert manifest["configuration"]["parameters"]["password"] == "[REDACTED]"
    assert manifest["configuration"]["parameters"]["credentials"] == "aws-prod"
    assert "secret" not in manifest["configuration"]["parameters"]["url"]
    assert "keep=yes" in manifest["configuration"]["parameters"]["url"]
    assert events == '{"message":"node ran"}\n'


def test_retry_attempts_and_events_are_preserved(tmp_path):
    spool = tmp_path / "task"
    spool.mkdir()
    events = spool / "info.log"
    archive = AttemptArchive("memory://archive-retry", "pipeline-id", "task-id", spool)

    archive.start_attempt({"started_at": "first"})
    events.write_text('{"message":"first"}\n', encoding="utf-8")
    archive.finalize(outcome="RETRY", celery_status="RETRY")

    events.write_text(
        '{"message":"first"}\n{"message":"second"}\n', encoding="utf-8"
    )
    second = AttemptArchive("memory://archive-retry", "pipeline-id", "task-id", spool)
    second.start_attempt({"started_at": "second"})
    second.finalize(outcome="SUCCESS", celery_status="SUCCESS")

    fs, root = fsspec.core.url_to_fs("memory://archive-retry")
    remote = Path(root) / "runs" / "pipeline-id" / "task-id"
    manifest = _remote_json(fs, str(remote / "manifest.json"))
    with fs.open(str(remote / "events.jsonl"), "r", encoding="utf-8") as stream:
        event = stream.read()

    assert [attempt["outcome"] for attempt in manifest["attempts"]] == [
        "RETRY",
        "SUCCESS",
    ]
    assert event == '{"message":"first"}\n{"message":"second"}\n'


def test_cross_worker_retry_merges_remote_events_into_new_spool(tmp_path):
    first_spool = tmp_path / "first"
    first_spool.mkdir()
    first_events = first_spool / "info.log"
    first_events.write_text('{"message":"first"}\n', encoding="utf-8")
    first = AttemptArchive("memory://archive-cross-worker", "pipeline-id", "task-id", first_spool)
    first.start_attempt({"started_at": "first"})
    first.finalize(outcome="RETRY", celery_status="RETRY")

    second_spool = tmp_path / "second"
    second_spool.mkdir()
    (second_spool / "info.log").write_text('{"message":"second"}\n', encoding="utf-8")
    second = AttemptArchive("memory://archive-cross-worker", "pipeline-id", "task-id", second_spool)
    second.start_attempt({"started_at": "second"})
    second.finalize(outcome="SUCCESS", celery_status="SUCCESS")

    fs, root = fsspec.core.url_to_fs("memory://archive-cross-worker")
    path = Path(root) / "runs" / "pipeline-id" / "task-id" / "events.jsonl"
    with fs.open(str(path), "r", encoding="utf-8") as stream:
        assert stream.read() == '{"message":"first"}\n{"message":"second"}\n'


def test_external_abort_snapshot_has_worker_time_but_no_pipeline_finish_time(tmp_path):
    spool = tmp_path / "task"
    archive = AttemptArchive("memory://archive-aborting", "pipeline-id", "task-id", spool)
    archive.start_attempt({"started_at": "now"})

    assert archive.finalize(
        outcome="ABORTING",
        worker_finished_at="2026-09-28T14:01:01+00:00",
    )

    fs, root = fsspec.core.url_to_fs("memory://archive-aborting")
    path = Path(root) / "runs" / "pipeline-id" / "task-id" / "manifest.json"
    manifest = _remote_json(fs, str(path))
    assert manifest["outcome"] == "ABORTING"
    assert manifest["finished_at"] is None
    assert manifest["worker_finished_at"] == "2026-09-28T14:01:01+00:00"


def test_archive_upload_failure_keeps_local_manifest_and_spool(tmp_path, monkeypatch):
    spool = tmp_path / "task"
    archive = AttemptArchive("memory://archive-failure", "pipeline-id", "task-id", spool)
    def fail_upload(*args, **kwargs):
        raise OSError("upload failed")

    monkeypatch.setattr(archive._fs, "put", fail_upload)

    assert not archive.start_attempt({"started_at": "now"})
    assert archive.failed
    assert (spool / "manifest.json").exists()
    assert (spool / "info.log").exists()


def test_remote_init_failure_still_finalizes_local_manifest(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    spool = tmp_path / "spool"
    archive = AttemptArchive(str(blocker / "remote"), "pipeline-id", "task-id", spool)

    assert not archive.start_attempt({"started_at": "now"})
    archive.update(outcome_hint="FAILURE")
    assert not archive.finalize(outcome="FAILURE", celery_status="FAILURE")

    manifest = json.loads((spool / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["outcome"] == "FAILURE"
    assert manifest["worker_finished_at"]


def test_sanitize_config_preserves_credential_reference_names():
    value = sanitize_config(
        {
            "credentials": "prod-s3",
            "url": "https://user:password@example.test/object?sig=secret&part=1",
        }
    )
    assert value["credentials"] == "prod-s3"
    assert "password" not in value["url"]
    assert "secret" not in value["url"]
    assert "part=1" in value["url"]
