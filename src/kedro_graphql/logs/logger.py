import redis
import redis.asyncio as redis_asyncio
import logging
from logging import LogRecord
from .json_log_formatter import JSONFormatter ## VerboseJSONFormatter also available
#from celery.signals import task_prerun, task_postrun
#from kedro_graphql.asgi import default_config as config
from typing import AsyncGenerator
from celery.result import AsyncResult
from celery.states import READY_STATES
import json
import os
from inspect import currentframe, getframeinfo

logger = logging.getLogger("kedro-graphql")
logger.setLevel(logging.INFO)

class RedisLogStreamPublisher(object):
    def __init__(self, topic, broker_url = None):
        self.connection = redis.Redis.from_url(broker_url)
        self.topic = topic
        if not self.connection.exists(self.topic):
            self.connection.xadd(self.topic, json.loads(JSONFormatter().format(LogRecord("kedro-graphql", 20, os.path.abspath(__file__), getframeinfo(currentframe()).lineno, "Starting log stream", None, None))))
            ## stream will expire in 24 hours (safety mechanism in case task_postrun fails to delete)
            self.connection.expire(self.topic, 86400)

    def publish(self, data):
        data = {k:(str(v) if isinstance(v, bool) else v) for k,v in data.items()}
        #print("PUBLISHING", type(data), data)
        self.connection.xadd(self.topic, data)

class RedisLogStreamSubscriber(object):
        
    @classmethod
    async def create(cls, topic, broker_url = None):
        """Factory method for async instantiation RedisLogStreamSubscriber objects.
        """
        self = RedisLogStreamSubscriber()
        self.topic = topic
        self.broker_url = broker_url
        self.connection = await redis_asyncio.from_url(broker_url)
        return self

    async def consume(self, count = 1, start_id = 0):
        r = await self.connection.xread(count = count, streams={self.topic:start_id})
        return r
    
class KedroGraphQLLogHandler(logging.StreamHandler):
    def __init__(self, topic, broker_url = None):
        logging.StreamHandler.__init__(self)
        self.broker_url = broker_url
        self.topic = topic
        self.broker = RedisLogStreamPublisher(topic, broker_url = broker_url)
        self.setFormatter(JSONFormatter())

    def emit(self, record):
        msg = self.format(record)
        self.broker.publish(json.loads(msg))


##@task_prerun.connect
##def setup_task_logger(task_id, task, args, **kwargs):
##    logger = logging.getLogger("kedro")
##
##    handler = KedroGraphQLLogHandler(task_id)
##    logger.addHandler(handler)
    
##@task_postrun.connect
##def cleanup_task_logger(task_id, task, args, **kwargs):
##    logger = logging.getLogger("kedro")
##    logger.info("Closing log stream")
##    for handler in logger.handlers:
##        if isinstance(handler, KedroGraphQLLogHandler) and handler.topic == task_id:
##            handler.flush()
##            handler.close()
##            handler.broker.connection.delete(task_id) ## delete stream
##            handler.broker.connection.close()
##    logger.handlers = []


class PipelineLogStream():

    @classmethod
    async def create(cls, task_id, broker_url = None):
        """Factory method for async instantiation PipelineLogStream objects.
        """
        self = PipelineLogStream()
        self.task_id = task_id
        self.broker_url = broker_url
        self.broker = await RedisLogStreamSubscriber().create(task_id, broker_url)
        return self

    async def consume(self) -> AsyncGenerator[dict, None]:
        start_id = 0
        while True:
            stream_data = await self.broker.consume(count = 1, start_id = start_id)
            if len(stream_data) > 0:
                for id, value in stream_data[0][1]:
                    yield {"task_id": self.task_id, "message_id": id.decode(), "message": value[b"message"].decode(), "time": value[b"time"].decode()}
                ## https://redis-py.readthedocs.io/en/stable/examples/redis-stream-example.html#read-more-data-from-the-stream
                start_id = stream_data[0][1][-1][0]
            else:
                ## check task status
                r = AsyncResult(self.task_id)
                if r.status in READY_STATES:
                    await self.broker.connection.close()
                    break
