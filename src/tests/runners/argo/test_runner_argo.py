from datetime import datetime
from unittest.mock import MagicMock

import pytest
from celery.result import AsyncResult

from kedro_graphql.runners.argo.argo import ArgoWorkflowsRunner

from .conftest import IN_DEV, REASON


def test_runner_labels_and_emits_authoritative_workflow_metadata():
    runner = ArgoWorkflowsRunner()
    runner.run_context = {
        "pipeline_id": "0123456789abcdef01234567",
        "task_id": "task:id",
    }
    order = []
    runner.emit_metadata = MagicMock(side_effect=lambda _: order.append("metadata"))
    submitted = {
        "metadata": {
            "namespace": "argo",
            "name": "generated-name",
            "uid": "workflow-uid",
            "creationTimestamp": "2026-09-10T12:00:00Z",
        }
    }
    reconciled = {
        **submitted,
        "status": {"phase": "Succeeded", "progress": "1/1"},
    }
    runner.create_workflow = MagicMock(return_value=submitted)
    runner.workflow_logs = MagicMock(side_effect=lambda _: order.append("logs"))
    runner.get_workflow = MagicMock(return_value=reconciled)
    pipeline = MagicMock()
    pipeline.nodes = []
    pipeline.inputs.return_value = set()
    pipeline.node_dependencies = {}

    runner._run(pipeline, MagicMock())

    manifest = runner.create_workflow.call_args.args[0]
    assert manifest["metadata"]["labels"] == {
        "kgql-pipeline": "0123456789abcdef01234567",
        "kgql-task": "task-id",
    }
    assert order[:2] == ["metadata", "logs"]
    runner.get_workflow.assert_called_once_with("generated-name")
    first, second = [call.args[0] for call in runner.emit_metadata.call_args_list]
    assert "x-argo-phase" not in first
    assert first["x-argo-workflow-name"] == "generated-name"
    assert first["x-argo-workflow-uid"] == "workflow-uid"
    assert second["x-argo-phase"] == "Succeeded"
    assert second["x-argo-workflow-name"] == "generated-name"
    assert second["x-argo-workflow-uid"] == "workflow-uid"
    assert second["x-argo-namespace"] == "argo"
    assert datetime.fromisoformat(second["x-argo-submitted-at"]).tzinfo is not None
    assert datetime.fromisoformat(second["x-argo-reconciled-at"]).tzinfo is not None


@pytest.mark.skipif(IN_DEV, reason=REASON)
@pytest.mark.usefixtures('celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
class TestArgoWorkflowRunner:
    @pytest.mark.asyncio
    async def test_runner(self, mock_pipeline_argo):
        """
        """
        # wait for task to finish
        r = AsyncResult(mock_pipeline_argo.task_id).get()

        # fetch result
        r = AsyncResult(mock_pipeline_argo.task_id)
        assert r.status == "SUCCESS"
