import json
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kedro_graphql.logs.logger import (
    KedroGraphQLLogHandler,
    PipelineLogStream,
    RedisLogStreamPublisher,
)


def test_redis_log_stream_preserves_nested_values():
    connection = Mock()
    connection.exists.return_value = True

    with patch(
        "kedro_graphql.logs.logger.redis.Redis.from_url", return_value=connection
    ):
        RedisLogStreamPublisher("task-id", "redis://localhost").publish(
            {
                "message": "hello",
                "context": {"node": "toy", "items": [1, True]},
                "enabled": True,
                "missing": None,
            }
        )

    connection.xadd.assert_called_once_with(
        "task-id",
        {
            "payload": json.dumps(
                {
                    "message": "hello",
                    "context": {"node": "toy", "items": [1, True]},
                    "enabled": True,
                    "missing": None,
                },
                separators=(",", ":"),
            )
        },
    )


def test_redis_failure_does_not_break_logging():
    with patch.object(RedisLogStreamPublisher, "__init__", return_value=None):
        handler = KedroGraphQLLogHandler("task-id")
    handler.broker = Mock()
    handler.broker.publish.side_effect = ConnectionError("redis unavailable")

    handler.emit(
        logging.LogRecord("pipeline", logging.INFO, __file__, 1, "hello", (), None)
    )


def test_redis_initialization_failure_does_not_break_logging():
    with patch.object(
        RedisLogStreamPublisher,
        "__init__",
        side_effect=ConnectionError("redis unavailable"),
    ):
        handler = KedroGraphQLLogHandler("task-id")

    assert handler.broker is None


@pytest.mark.asyncio
async def test_pipeline_log_stream_decodes_structured_payload():
    stream = PipelineLogStream()
    stream.task_id = "task-id"
    stream.broker = Mock()
    stream.broker.consume = AsyncMock(
        return_value=[
            (
                b"task-id",
                [
                    (
                        b"1-0",
                        {
                            b"payload": json.dumps(
                                {
                                    "message": "node running",
                                    "time": "2025-01-01T12:30:45.250000+00:00",
                                    "context": {"node": "toy"},
                                }
                            ).encode(),
                        },
                    )
                ],
            )
        ]
    )
    stream.broker.connection.aclose = AsyncMock()

    consumer = stream.consume()
    try:
        assert await consumer.__anext__() == {
            "task_id": "task-id",
            "message_id": "1-0",
            "message": "node running",
            "time": "2025-01-01T12:30:45.250000+00:00",
        }
    finally:
        await consumer.aclose()


@pytest.mark.usefixtures('mock_celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('depends_on_current_app')
class TestPipelineLogStream:
    @pytest.mark.asyncio
    async def test_consume(self, mock_app, mock_pipeline):
        """Requires Redis to run.
        """
        task_id = mock_pipeline.status[-1].task_id
        subscriber = await PipelineLogStream().create(task_id=task_id, broker_url=mock_app.state.services.config.broker)
        async for e in subscriber.consume():
            assert set(e.keys()) == set(["task_id", "message_id", "message", "time"])
