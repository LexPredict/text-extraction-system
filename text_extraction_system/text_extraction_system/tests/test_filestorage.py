from unittest.mock import patch

from webdav3.client import Client

from text_extraction_system import config
from text_extraction_system.file_storage import get_webdav_client


@patch.object(config,
              attribute='_settings',
              new=config.Settings.construct(webdav_url='', webdav_username='', webdav_password=''))
@patch.object(Client, attribute='download', autospec=True)
def test_webdav_client_init_no_config_file(client_download):
    webdav_client = get_webdav_client()
    with webdav_client.get_as_local_fn('something'):
        pass
    client_download.assert_called_once()
