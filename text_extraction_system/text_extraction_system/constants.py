metadata_fn = 'metadata.json'
results_fn = 'results.zip'
pages_ocred = 'pages_ocred'
pages_for_processing = 'pages_for_processing'
pages_tables = 'pages_tables'
from_original_doc = 'from_original_doc.pickle'
task_ids = 'task_ids'

tasks_pending = 'tasks_pending'
queue_celery_beat = 'beat'

TESSERACT_LANGUAGES = {
    "en": "eng",
    "it": "ita",
    "fr": "fra",
    "es": "spa",
    "de": "deu",
    "ru": "rus"
}

TESSERACT_DEFAULT_LANGUAGE = "eng"

# that flag corresponds to ImageAberrationDetection.detect_rotation_using_skewlib
ROTATION_DETECTION_DESKEW = 'deskew'

# that flag corresponds to ImageAberrationDetection.detect_rotation_most_frequent
ROTATION_DETECTION_TILE_DESKEW = 'tile_deskew'

# that flag corresponds to ImageAberrationDetection.detect_rotation_dilated_rows
ROTATION_DETECTION_DILATED_ROWS = 'dilated_rows'
