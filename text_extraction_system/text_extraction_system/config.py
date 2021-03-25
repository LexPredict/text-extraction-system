import os

from pydantic import BaseSettings

project_root = os.path.dirname(os.path.join(os.path.dirname(__file__)))


class Settings(BaseSettings):
    celery_broker: str
    celery_backend: str
    webdav_url: str
    webdav_username: str
    webdav_password: str
    java_modules_path: str = os.path.join(project_root, 'java_modules')
    text_extraction_system_ui_path: str = os.path.join(project_root, 'text_extraction_system_ui')
    fasttext_lang_model: str = os.path.join(project_root, 'models/lid.176.bin')
    delete_temp_files_on_request_finish: bool = True
    keep_failed_files: bool = False
    celery_shutdown_when_no_tasks_longer_than_sec: int = None

    log_to_stdout: bool = True
    log_to_stdout_json: bool = True
    log_to_file: str = None

    class Config:
        env_prefix = 'text_extraction_system_'


_settings: Settings = None


def get_settings():
    global _settings
    if not _settings:
        _settings = Settings(_env_file='.env')
    return _settings
