import redis
import logging
from .json_log_formatter import JSONFormatter
from celery.signals import task_prerun, task_postrun
from kedro_graphql.config import config
from typing import AsyncGenerator
from celery.result import AsyncResult
from celery.states import READY_STATES
import json

logger = logging.getLogger("kedro-graphql")

class RedisLogStream(object):
    def __init__(self, topic, broker_url = config["KEDRO_GRAPHQL_CELERY_BROKER"]):
        self.connection = redis.Redis.from_url(broker_url)
        self.topic = topic

    def emit(self, data):
        self.connection.xadd(self.topic, data)
    
    def consume(self, count = 1, start_id = 0):
        r = self.connection.xread(count = count, streams={self.topic:start_id})
        return r
    
class KedroGraphQLLogHandler(logging.StreamHandler):
    def __init__(self, topic, broker_url = config["KEDRO_GRAPHQL_CELERY_BROKER"]):
        logging.StreamHandler.__init__(self)
        self.broker_url = broker_url
        self.topic = topic
        self.broker = RedisLogStream(topic, broker_url)
        self.setFormatter(JSONFormatter())

    def emit(self, record):
        msg = self.format(record)
        self.broker.emit(json.loads(msg))


@task_prerun.connect
def setup_task_logger(task_id, task, args, **kwargs):
    logger = logging.getLogger("kedro")

    handler = KedroGraphQLLogHandler(task_id)
    logger.addHandler(handler)
    
@task_postrun.connect
def cleanup_task_logger(task_id, task, args, **kwargs):
    logger = logging.getLogger("kedro")
    for handler in logger.handlers:
        handler.flush()
        handler.close()
    logger.handlers = []


class PipelineLogStream():

    def __init__(self, task_id = None, broker_url = config["KEDRO_GRAPHQL_CELERY_BROKER"]):
        self.broker = RedisLogStream(task_id, broker_url)
        self.task_id = task_id

    async def consume(self) -> AsyncGenerator[dict, None]:
        start_id = 0
        while True:
            stream_data = self.broker.consume(count = 1, start_id = start_id)
            if len(stream_data) > 0:
                for id, value in stream_data[0][1]:
                    yield {"task_id": self.task_id, "message_id": id.decode(), "message": value}
                ## https://redis-py.readthedocs.io/en/stable/examples/redis-stream-example.html#read-more-data-from-the-stream
                start_id = stream_data[0][1][-1][0]
            else:
                ## check task status
                r = AsyncResult(self.task_id)
                if r.status in READY_STATES:
                    break