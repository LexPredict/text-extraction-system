from pydantic import BaseSettings


class Settings(BaseSettings):
    celery_broker: str
    celery_backend: str
    webdav_url: str
    webdav_username: str
    webdav_password: str

    class Config:
        env_prefix = 'text_extraction_system_'


settings = Settings(_env_file='.env')
