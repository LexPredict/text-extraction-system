import logging
import os

import requests

from integration_tests.testing_config import test_settings

log = logging.getLogger(__name__)
if __name__ == '__main__':
    fn = os.path.join(os.path.dirname(__file__), 'data', 'tables.pdf')
    call_back_data = {
        'call_back_celery_broker': 'amqp://contrax1:contrax1@127.0.0.1:56720/contrax1_vhost',
        'call_back_celery_queue': 'default',
        'call_back_celery_task_name': 'document.process_text_extraction_results'
    }
    requests.post(test_settings.api_url + '/api/v1/data_extraction_tasks/',
                  files=dict(file=(os.path.basename(fn), open(fn, 'rb'))), data=call_back_data)
