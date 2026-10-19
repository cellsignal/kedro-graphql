from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kedro_graphql.celeryapp import celery_app
from kedro_graphql.config import KedroGraphQLConfig
from kedro_graphql.models import Pipeline, PipelineStatus, State, Tag
from kedro_graphql.pipeline_visibility import pipeline_name_allowed, pipeline_submission_name_allowed
from kedro_graphql.schema import Query
from kedro_graphql.tasks import KedroGraphqlTask, _pipeline_tag_entries


def test_submission_eligibility_does_not_hide_history():
    config = KedroGraphQLConfig(pipeline_submission_name_allowlist=["qc"])
    assert pipeline_name_allowed(config, "pcr")
    assert not pipeline_submission_name_allowed(config, "pcr")
    assert pipeline_submission_name_allowed(config, "qc")
    config.pipeline_name_disallowlist = ["qc"]
    assert not pipeline_submission_name_allowed(config, "qc")
    config.pipeline_submission_name_allowlist = []
    assert not pipeline_submission_name_allowed(config, "anything")


def test_submission_templates_filter_before_pagination():
    config = KedroGraphQLConfig(pipeline_submission_name_allowlist=["qc", "qc2"])
    templates = [SimpleNamespace(id=id, name=name) for id, name in [("a", "pcr"), ("b", "qc"), ("c", "qc2")]]
    services = SimpleNamespace(config=config, metadata=SimpleNamespace(templates=templates))
    info = SimpleNamespace(context=SimpleNamespace(request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(services=services)))))
    first = Query().pipeline_submission_templates(info, limit=1)
    assert first.pipeline_templates == [templates[1]]
    second = Query().pipeline_submission_templates(info, limit=1, cursor=first.page_meta.next_cursor)
    assert second.pipeline_templates == [templates[2]]
    assert second.page_meta.next_cursor is None
    with pytest.raises(ValueError, match="limit"):
        Query().pipeline_submission_templates(info, limit=0)


def test_custom_celery_imports_keep_core_tasks():
    config = KedroGraphQLConfig(celery_task_imports=["molbio.cloning_submission", "kedro_graphql.tasks"])
    app = celery_app(config, None, "/tmp")
    assert app.conf.imports == ("kedro_graphql.tasks", "molbio.cloning_submission")
    app.close()


@pytest.mark.parametrize("values", [None, [{"key": "x", "value": ["y"]}], [{"key": "", "value": "y"}], [{"key": "x", "value": "y", "extra": 1}], [{"key": "x", "value": "y"}] * 1001])
def test_tag_events_validate_payload(values):
    with pytest.raises(ValueError):
        _pipeline_tag_entries(values)


def test_tag_events_merge_and_reject_stale_task():
    pipeline = Pipeline(name="qc", tags=[Tag(key="user", value="kept"), Tag(key="barcode", value="ABP1")], status=[PipelineStatus(state=State.STARTED, task_id="task")])
    task = KedroGraphqlTask()
    task._db = SimpleNamespace(read=AsyncMock(return_value=pipeline))
    with patch.object(task, "_update_current", Mock(return_value=pipeline)) as update:
        task._persist_pipeline_tags(pipeline.id, "task", [{"key": "barcode", "value": "ABP1"}, {"key": "barcode", "value": "ABP2"}])
        assert [(tag.key, tag.value) for tag in pipeline.tags] == [("user", "kept"), ("barcode", "ABP1"), ("barcode", "ABP2")]
        update.assert_called_once()
        update.reset_mock()
        task._persist_pipeline_tags(pipeline.id, "other-task", [{"key": "barcode", "value": "ABP3"}])
        update.assert_not_called()
