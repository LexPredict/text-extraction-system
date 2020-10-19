from pydantic import BaseSettings


class TestSettings(BaseSettings):
    api_url: str
    call_back_server_bind_host: str
    call_back_server_bind_port: int

    class Config:
        env_prefix = 'testing_'


test_settings = TestSettings(_env_file='.test_env')
