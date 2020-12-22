import logging
import platform
from typing import List, Dict
from uuid import uuid4

from kombu import Connection

log = logging.getLogger(__name__)


def send_task(broker_url: str,
              queue: str,
              task_name: str,
              task_args: List = None,
              task_kwargs: Dict = None,
              task_id: str = None,
              root_task_id: str = None,
              parent_task_id: str = None,
              celery_version: int = 4):
    if celery_version != 4:
        log.warning(f'Warning: This celery client was tested only with Celery 4.4.'
                    f'Though it may work with version {celery_version} too.')
    send_task_celery4(broker_url=broker_url,
                      queue=queue,
                      task_name=task_name,
                      task_args=task_args,
                      task_kwargs=task_kwargs,
                      task_id=task_id,
                      root_task_id=root_task_id,
                      parent_task_id=parent_task_id)


def send_task_celery4(broker_url: str,
                      queue: str,
                      task_name: str,
                      task_args: List = None,
                      task_kwargs: Dict = None,
                      task_id: str = None,
                      root_task_id: str = None,
                      parent_task_id: str = None):
    """
    Schedule a celery task in a different Celery without initializing/registering a new Celery app
    or having access to the destination app sources.
    Implemented by investigating what Celery sends into Kombu.
    Tested with Celery 4.4.6. May be compatible or incompatible with other Celery versions.
    """
    with Connection(broker_url) as conn:
        task_id = task_id or str(uuid4())
        task_args = task_args or ()
        task_kwargs = task_kwargs or dict()
        producer = conn.Producer(serializer='json')
        body = (task_args, task_kwargs,
                {'callbacks': None, 'errbacks': None, 'chain': None, 'chord': None})
        headers = {'lang': 'py',
                   'task': task_name,
                   'id': task_id,
                   'root_id': root_task_id,
                   'parent_id': parent_task_id,
                   'args_repr': repr(task_args),
                   'kwargs_repr': repr(task_kwargs),
                   'origin': platform.node()
                   }
        retry_policy = {'max_retries': 3, 'interval_start': 0, 'interval_max': 1, 'interval_step': 0.2}
        producer.publish(body, routing_key=queue, delivery_mode=2, serializer='json',
                         headers=headers, exchange='', retry=True, retry_policy=retry_policy)
