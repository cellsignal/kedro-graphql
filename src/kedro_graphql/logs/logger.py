import json
import logging
import os
from inspect import currentframe, getframeinfo
from logging import LogRecord
from typing import AsyncGenerator

import redis
import redis.asyncio as redis_asyncio
from celery.result import AsyncResult
from celery.states import READY_STATES
from starlette.concurrency import run_in_threadpool

from .json_log_formatter import JSONFormatter  # VerboseJSONFormatter also available

logger = logging.getLogger("kedro_graphql")
logger.setLevel(logging.INFO)


class RedisLogStreamPublisher(object):
    def __init__(self, topic, broker_url=None):
        self.connection = redis.Redis.from_url(broker_url)
        self.topic = topic
        if not self.connection.exists(self.topic):
            bootstrap_payload = json.loads(
                JSONFormatter().format(
                    LogRecord(
                        "kedro_graphql",
                        20,
                        os.path.abspath(__file__),
                        getframeinfo(currentframe()).lineno,
                        "Starting log stream",
                        None,
                        None,
                    )
                )
            )
            self._xadd(bootstrap_payload)
            # Safety net if task cleanup fails to delete the stream.
            self.connection.expire(self.topic, 86400)

    def publish(self, data):
        self._xadd(data)

    def _xadd(self, data):
        self.connection.xadd(
            self.topic,
            {"payload": json.dumps(data, separators=(",", ":"), default=str)},
        )


class RedisLogStreamSubscriber(object):

    @classmethod
    async def create(cls, topic, broker_url=None):
        """Factory method for async instantiation RedisLogStreamSubscriber objects.
        """
        self = RedisLogStreamSubscriber()
        self.topic = topic
        self.broker_url = broker_url
        self.connection = await redis_asyncio.from_url(broker_url)
        return self

    async def consume(self, count=1, start_id=0):
        r = await self.connection.xread(count=count, streams={self.topic: start_id})
        return r


class KedroGraphQLLogHandler(logging.StreamHandler):
    def __init__(self, topic, broker_url=None):
        logging.StreamHandler.__init__(self)
        self.broker_url = broker_url
        self.topic = topic
        try:
            self.broker = RedisLogStreamPublisher(topic, broker_url=broker_url)
        except Exception:
            self.broker = None
            self.handleError(logging.LogRecord(
                __name__, logging.ERROR, __file__, 0,
                "Unable to initialize pipeline log stream", (), None,
            ))
        self.setFormatter(JSONFormatter())

    def emit(self, record):
        if self.broker is None:
            return
        try:
            payload = json.loads(self.format(record))
            self.broker.publish(payload)
        except Exception:
            self.handleError(record)


class PipelineLogStream():

    @classmethod
    async def create(cls, task_id, broker_url=None):
        """Factory method for async instantiation PipelineLogStream objects.
        """
        self = PipelineLogStream()
        self.task_id = task_id
        self.broker_url = broker_url
        self.broker = await RedisLogStreamSubscriber().create(task_id, broker_url)
        return self

    async def consume(self) -> AsyncGenerator[dict, None]:
        start_id = 0
        try:
            while True:
                stream_data = await self.broker.consume(count=1, start_id=start_id)
                if len(stream_data) > 0:
                    for id, value in stream_data[0][1]:
                        try:
                            payload = json.loads(value[b"payload"])
                            if not isinstance(payload, dict):
                                raise ValueError(
                                    "pipeline log payload must be an object"
                                )
                        except (KeyError, TypeError, UnicodeDecodeError, ValueError):
                            logger.warning(
                                "Skipping malformed pipeline log stream entry"
                            )
                            continue

                        yield {
                            "task_id": self.task_id,
                            "message_id": id.decode(),
                            "message": payload.get("message", ""),
                            "time": payload.get("time", ""),
                        }
                    # https://redis-py.readthedocs.io/en/stable/examples/redis-stream-example.html#read-more-data-from-the-stream
                    start_id = stream_data[0][1][-1][0]
                else:
                    # check task status - wrap blocking Celery operation in thread pool
                    def check_task_status(task_id):
                        try:
                            r = AsyncResult(task_id)
                            # Check if backend is disabled/not available
                            if not hasattr(r.backend, '_get_task_meta_for'):
                                # No result backend configured, can't check status
                                # Return None to indicate we should keep streaming
                                return None
                            return r.status
                        except (AttributeError, NotImplementedError):
                            # Backend doesn't support status checking
                            return None

                    status = await run_in_threadpool(check_task_status, self.task_id)
                    # End streaming on normal terminal states and explicit ABORTED
                    # (used by abortable tasks in some backends).
                    terminal_statuses = set(READY_STATES).union({"ABORTED"})
                    # If status is None (no backend), continue streaming.
                    if status is not None and status in terminal_statuses:
                        break
        finally:
            # Always close async Redis connection, including cancellation/disconnect.
            await self.broker.connection.aclose()
