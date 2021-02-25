metadata_fn = 'metadata.json'
results_fn = 'results.zip'
pages_ocred = 'pages_ocred'
pages_for_processing = 'pages_for_processing'
pages_tables = 'pages_tables'
from_original_doc = 'from_original_doc.pickle'
task_ids = 'task_ids'

tasks_pending = 'tasks_pending'
queue_celery_beat = 'beat'

synchronous_api_sleep_delays_sec = {
    0: 3,
    30: 5,
    5*60: 10,
    15*60: 15,
}
