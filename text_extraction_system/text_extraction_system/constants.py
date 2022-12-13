metadata_fn = 'metadata.json'
results_fn = 'results.zip'
pages_ocred = 'pages_ocred'
pages_for_processing = 'pages_for_processing'
pages_tables = 'pages_tables'
from_original_doc = 'from_original_doc.pickle'
task_ids = 'task_ids'

tasks_pending = 'tasks_pending'
queue_celery_beat = 'beat'

PAGE_SEPARATOR = '\n\n\f'
DPI: int = 300

TESSERACT_LANGUAGES = {
    "en": "eng",
    "it": "ita",
    "fr": "fra",
    "es": "spa",
    "de": "deu",
    "ru": "rus"
}

TESSERACT_DEFAULT_LANGUAGE = "osd"
