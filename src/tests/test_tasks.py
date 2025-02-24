import json

import pytest

from kedro_graphql.models import (
    DataSet,
    Parameter,
    Pipeline,
    PipelineStatus,
    State,
    Tag,
)
from kedro_graphql.tasks import run_pipeline


@pytest.mark.usefixtures('mock_celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('depends_on_current_app')
@pytest.mark.asyncio
async def test_run_pipeline(mock_app, mock_text_in, mock_text_out):
    """
    This test will fail because the pipeline is missing in the backend
    """
    inputs = [{"name": "text_in", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_in)})}]
    outputs = [{"name": "text_out", "config": json.dumps({"type": "text.TextDataset", "filepath": str(mock_text_out)})}]
    parameters = [{"name": "example", "value": "hello"}]
    tags = [{"key": "author", "value": "opensean"}, {"key": "package", "value": "kedro-graphql"}]

    p = Pipeline(
        name="example00",
        data_catalog=[DataSet(**i) for i in inputs] + [DataSet(**o) for o in outputs],
        parameters=[Parameter(**p) for p in parameters],
        tags=[Tag(**p) for p in tags],
        status=[PipelineStatus(state=State.STAGED,
                               runner="kedro.runner.SequentialRunner",
                               session=None,
                               started_at=None,
                               finished_at=None,
                               task_id=None,
                               task_name=None)]
    )

    p = mock_app.backend.create(p)
    serial = p.serialize()

    result = run_pipeline.delay(
        id=str(p.id),
        name=serial["name"],
        data_catalog=serial["data_catalog"],
        parameters=serial["parameters"],
        runner="kedro.runner.SequentialRunner"
    )
    result = result.wait(timeout=None, interval=0.5)
