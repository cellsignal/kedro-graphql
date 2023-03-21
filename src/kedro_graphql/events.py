from queue import Queue
from queue import Empty as QueueEmptyException
from threading import Thread
import logging
from typing import AsyncGenerator
from celery.states import READY_STATES, EXCEPTION_STATES

logger = logging.getLogger("kedro-graphql")

class PipelineEventMonitor:
    def __init__(self, app = None, task_id = None, timeout = 1):
        """
        Kwargs:
            app (Celery): celery application instance.
            uuid (str): a celery task id.
            timeout (float): See https://docs.python.org/3/library/queue.html#queue.Queue.get
        """
        self.task_id = task_id
        self.app = app
        self.timeout = timeout

    @staticmethod
    def _task_event_receiver(app, queue, task_id):
        """
        Recieves task events from backend broker and puts them in a 
        Queue.  Incoming tasks are filtered and only tasks with a 
        root_id or uuid matching the provided id are put in the Queue.

        Example event payloads:
    
        {'hostname': 'gen36975@alligator', 'utcoffset': 5, 'pid': 36975, 'clock': 7864, 'uuid': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'root_id': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'parent_id': None, 'name': 'kedro_graphql.tasks.run_pipeline', 'args': '()', 'kwargs': "{'name': 'example00', 'inputs': {'text_in': {'type': 'text.TextDataSet', 'filepath': './data/01_raw/text_in.txt'}}, 'outputs': {'text_out': {'type': 'text.TextDataSet', 'filepath': './data/02_intermediate/text_out.txt'}}}", 'retries': 0, 'eta': None, 'expires': None, 'queue': 'celery', 'exchange': '', 'routing_key': 'celery', 'timestamp': 1672860581.1371481, 'type': 'task-sent', 'local_received': 1672860581.138474}
        {'hostname': 'celery@alligator', 'utcoffset': 5, 'pid': 37029, 'clock': 7867, 'uuid': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'timestamp': 1672860581.1411166, 'type': 'task-started', 'local_received': 1672860581.144976}
        {'hostname': 'celery@alligator', 'utcoffset': 5, 'pid': 37029, 'clock': 7870, 'uuid': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'result': "'success'", 'runtime': 2.013245126003312, 'timestamp': 1672860583.1549191, 'type': 'task-succeeded', 'local_received': 1672860583.158338}
        
        Args:
            app (Celery): celery application instance.
            queue (Queue):  a python queue.Queue.
            task_id (str):  celery task id.
        
        """
        
        def process_tasks(event):
            if event.get("root_id", "") == task_id or event.get("uuid") == task_id:    
                queue.put(event)
    
    
        with app.connection() as connection:
            recv = app.events.Receiver(connection, handlers={
                    'task-sent': process_tasks,
                    'task-recieved': process_tasks,
                    'task-started': process_tasks,
                    'task-succeeded': process_tasks,
                    'task-failed': process_tasks,
                    'task-rejected': process_tasks,
                    'task-revoked': process_tasks,
                    'task-retried': process_tasks
            })
    
            recv.capture(limit=None, timeout=None, wakeup=True)
    
    def _start_task_event_receiver_thread(self, queue):
        """
        Start the task event receiver in a thread.

        Args:
            queue (Queue): a python queue.Queue.

        Returns:
            worker (threading.Thread): a python thread object.

        """
        worker = Thread(target=self._task_event_receiver, args=(self.app,queue,self.task_id))
        worker.daemon = True
        worker.start()
        logger.info("started event reciever thread")
        return worker
    
    async def consume(self) -> AsyncGenerator[dict, None]:
        """
        """
        q = Queue()
    
        event_thread = self._start_task_event_receiver_thread(q)
        ## https://docs.celeryq.dev/en/stable/reference/celery.events.state.html#module-celery.events.state
        state = self.app.events.State()
    
        while True:
            try:
                event = q.get(timeout = self.timeout)
                state.event(event)
                # task name is sent only with -received event, and state
                # will keep track of this for us.
                task = state.tasks.get(event['uuid'])
                yield {"task_id": task.id, "status": task.state, "result": task.result, "timestamp": task.timestamp, "traceback": task.traceback}
                q.task_done()
                if task.state in READY_STATES:
                    break
            except QueueEmptyException:
                if self.app.AsyncResult(self.task_id).status in READY_STATES:
                    break
                else:
                    continue

        event_thread.join(timeout = 0.1)
          