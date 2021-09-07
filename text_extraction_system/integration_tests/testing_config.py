from pydantic import BaseSettings


class TestingSettings(BaseSettings):
    api_url: str
    call_back_server_bind_host: str
    call_back_server_bind_port: int
    username: str = None
    password: str = None

    class Config:
        env_prefix = 'testing_'


test_settings = TestingSettings(_env_file='.test_env')
