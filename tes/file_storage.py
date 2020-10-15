from webdav3.client import Client

from .config import settings

options = {
    'webdav_hostname': settings.webdav_url,
    'webdav_login': settings.webdav_username,
    'webdav_password': settings.webdav_password
}

webdav_client = Client(options)
