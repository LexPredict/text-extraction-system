import os

from pydantic import BaseSettings

project_root = os.path.dirname(os.path.join(os.path.dirname(__file__)))


class Settings(BaseSettings):
    celery_broker: str
    celery_backend: str
    webdav_url: str
    webdav_username: str
    webdav_password: str
    tika_jar_path: str = os.path.join(project_root, './tika')
    tika_config: str = os.path.join(project_root, './tika/tika.lexp.no.ocr.config')
    fasttext_lang_model: str = os.path.join(project_root, './models/lid.176.bin')
    delete_temp_files_on_request_finish: bool = True

    class Config:
        env_prefix = 'text_extraction_system_'


_settings: Settings = None


def get_settings():
    global _settings
    if not _settings:
        _settings = Settings(_env_file='.env')
    return _settings
