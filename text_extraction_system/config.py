from pydantic import BaseSettings


class Settings(BaseSettings):
    celery_broker: str
    celery_backend: str
    webdav_url: str
    webdav_username: str
    webdav_password: str
    split_pdf_to_pages_block_size: int = 10

    class Config:
        env_prefix = 'text_extraction_system_'


_settings: Settings = None


def get_settings():
    global _settings
    if not _settings:
        _settings = Settings(_env_file='.env')
    return _settings
