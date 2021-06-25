from pydantic import BaseSettings


class TestingSettings(BaseSettings):
    api_url: str = 'http://127.0.0.1:8000'
    call_back_server_bind_host: str = '127.0.0.1'
    call_back_server_bind_port: int = 54321
    username: str = None
    password: str = None

    class Config:
        env_prefix = 'testing_'


test_settings = TestingSettings(_env_file='.test_env')
