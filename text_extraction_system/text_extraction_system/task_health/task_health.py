import json
from datetime import datetime
from logging import Logger, getLogger
from typing import List, Dict
from typing import Set, Optional, Tuple

from kombu import Connection
from redis import Redis
from webdav3.exceptions import RemoteResourceNotFound

from text_extraction_system.config import get_settings
from text_extraction_system.constants import tasks_pending, queue_celery_beat
from text_extraction_system.file_storage import get_webdav_client


def init_task_tracking(*args, **kwargs):
    get_webdav_client().mkdir(tasks_pending)


def store_pending_task_info_in_webdav(body,
                                      exchange,
                                      routing_key,
                                      headers,
                                      properties,
                                      declare,
                                      retry_policy):
    if routing_key == queue_celery_beat:
        # don't track Celery Beat tasks as they are not going through the default queue in Redis
        return

    # structures are described here:
    # https://docs.celeryproject.org/en/stable/internals/protocol.html#message-protocol-task-v2
    webdav_client = get_webdav_client()
    task_info = dict(exchange=exchange,
                     routing_key=routing_key,
                     headers=headers,
                     body=body,
                     retry_policy=retry_policy,
                     properties=properties)
    task_id = headers['id']
    webdav_client.pickle(obj=task_info, remote_path=f'{tasks_pending}/{task_id}')


def remove_pending_task_info_from_webdav(task_id: str, task_name: str):
    try:
        get_webdav_client().clean(f'{tasks_pending}/{task_id}')
    except RemoteResourceNotFound:
        pass


def get_scheduled_tasks_from_redis() -> Set[str]:
    conf = get_settings()
    broker_url = conf.celery_broker
    r = Redis.from_url(broker_url)
    return {json.loads(item)['headers']['id'] for item in r.lrange('celery', 0, -1)}


def get_pending_tasks_from_webdav() -> Set[str]:
    webdav = get_webdav_client()
    return set(webdav.list(remote_path=tasks_pending, get_info=False))


def get_unknown_pending_tasks() -> Set[str]:
    pending_from_webdav = get_pending_tasks_from_webdav()
    scheduled_from_redis = get_scheduled_tasks_from_redis()
    pending_from_webdav.difference_update(scheduled_from_redis)
    return pending_from_webdav


def re_schedule_unknown_pending_tasks(log: Logger) -> List[Tuple[str, str]]:
    conf = get_settings()
    webdav_client = get_webdav_client()
    broker_url = conf.celery_broker
    if not broker_url.startswith('redis:'):
        raise Exception('Only Redis broker supported for the task health tracking.')
    restarted_tasks: List[Tuple[str, str]] = list()
    failed_to_restart_tasks: List[Tuple[str, str]] = list()
    start_time = datetime.now()
    unknown_pending_tasks = get_unknown_pending_tasks()
    for task_id in unknown_pending_tasks:
        task_name: Optional[str] = 'unknown'
        try:
            task_info: Dict = webdav_client.unpickle(remote_path=f'{tasks_pending}/{task_id}')
            task_name = task_info['headers']['task'] or 'unknown'

            with Connection(broker_url) as conn:
                producer = conn.Producer(serializer='json')
                producer.publish(task_info['body'],
                                 routing_key=task_info['routing_key'],
                                 delivery_mode=2,
                                 serializer='pickle',
                                 headers=task_info['headers'],
                                 exchange=task_info['exchange'],
                                 retry=task_info['retry_policy'] is not None,
                                 retry_policy=task_info['retry_policy'])
                restarted_tasks.append((task_id, task_name))

        except Exception as ex:
            failed_to_restart_tasks.append((task_id, task_name))
            log.error(f'Unable to restart lost pending task: #{task_id} - {task_name}', exc_info=ex)
    if unknown_pending_tasks:
        time_spent = datetime.now() - start_time
        msg = f'Found {len(unknown_pending_tasks)} and restarted {len(restarted_tasks)} unknown/lost tasks ' \
              f'registered at Webdav but not found in Redis queue.\n' \
              f'Time spent: {time_spent}\n'
        if restarted_tasks:
            msg += f'Restarted tasks:\n' + '\n'.join([' - '.join(item) for item in restarted_tasks])
        if failed_to_restart_tasks:
            msg += f'Failed to restart tasks:\n' + '\n'.join([' - '.join(item) for item in failed_to_restart_tasks])
        log.info(msg)
    return restarted_tasks


if __name__ == '__main__':
    print(re_schedule_unknown_pending_tasks(getLogger(__file__)))
