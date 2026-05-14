import asyncio
import logging
from datetime import datetime, timezone
from queue import Empty as QueueEmptyException
from queue import Queue
from threading import Thread
from typing import AsyncGenerator

from celery.states import READY_STATES
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("kedro-graphql")


class PipelineEventMonitor:
    def __init__(self, app=None, task_id=None, timeout=1):
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
        worker = Thread(target=self._task_event_receiver,
                        args=(self.app, queue, self.task_id))
        worker.daemon = True
        worker.start()
        logger.info("started event reciever thread")
        return worker

    async def consume(self) -> AsyncGenerator[dict, None]:
        q = Queue()

        event_thread = self._start_task_event_receiver_thread(q)
        # https://docs.celeryq.dev/en/stable/reference/celery.events.state.html#module-celery.events.state
        state = self.app.events.State()

        while True:
            try:
                event = q.get(timeout=self.timeout)
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

        event_thread.join(timeout=0.1)

    async def start(self, interval=0.5) -> AsyncGenerator[dict, None]:
        """
        A simplified but fully async version of the PipelineEventMonitor().consume() method.

        The PipelineEventMonitor.consume() method relies on celery's native
        real time event processing approach which is syncronous and blocking.
        https://docs.celeryq.dev/en/stable/userguide/monitoring.html#real-time-processing

        """

        def get_task_state(app, task_id):
            """Helper to get task state in thread pool - Celery AsyncResult properties are blocking."""
            try:
                task = app.AsyncResult(task_id)

                # Check if backend is disabled/not available
                if not hasattr(task.backend, '_get_task_meta_for'):
                    # No result backend configured, return pending status
                    return {
                        "task_id": task_id,
                        "status": "PENDING",
                        "result": "No result backend configured",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "traceback": None
                    }
                # if task result is None and status is "ABORTED", change status to "ABORTING" to indicate that the task is in the process of being aborted
                # celery doesn't have "ABORTING" status
                if task.status == "ABORTED" and task.result is None:
                    return {
                        "task_id": task_id,
                        "status": "ABORTING",
                        "result": None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "traceback": None
                    }
                return {
                    "task_id": task.id,
                    "status": task.state,
                    "result": str(task.result),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "traceback": task.traceback
                }
            except (AttributeError, NotImplementedError) as e:
                # Backend doesn't support status checking
                return {
                    "task_id": task_id,
                    "status": "PENDING",
                    "result": f"Backend error: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "traceback": None
                }

        while True:
            # Run blocking Celery AsyncResult access in thread pool
            task_state = await run_in_threadpool(get_task_state, self.app, self.task_id)
            yield task_state
            
            if task_state["status"] in READY_STATES:
                if task_state["result"] == "aborted":
                    yield {
                    "task_id": task_state["task_id"],
                    "status": "ABORTED",
                    "result": str(task_state["result"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "traceback": task_state["traceback"]
                }
                break
            await asyncio.sleep(interval)
