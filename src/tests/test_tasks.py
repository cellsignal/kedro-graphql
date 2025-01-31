import pytest
from kedro_graphql.tasks import run_pipeline



@pytest.mark.usefixtures('mock_celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('depends_on_current_app')
@pytest.mark.asyncio
async def test_run_pipeline(mock_text_in, mock_text_out):

    result = run_pipeline.delay(
        name = "example00", 
        data_catalog = {"text_in":{"type": "text.TextDataset", "filepath": str(mock_text_in)},
                        "text_out": {"type": "text.TextDataset", "filepath": str(mock_text_out)}},
        parameters = {"example": "hello",
                      "duration": 0.1},
        runner = "kedro.runner.SequentialRunner",
        session_id = "00001"
    )
    result = result.wait(timeout=None, interval=0.5)
    print(result)