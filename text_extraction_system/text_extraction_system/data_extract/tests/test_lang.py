from unittest.mock import patch

from text_extraction_system import config
from text_extraction_system.data_extract.lang import get_lang_detector


@patch.object(config,
              attribute='_settings',
              new=config.Settings.construct(webdav_url='', webdav_username='', webdav_password=''))
def test_lang_detection1():
    lang_detector = get_lang_detector()
    text = 'emotionale Bedingungen Fruchtbarkeit'
    assert lang_detector.predict_lang(text) == 'de'


@patch.object(config,
              attribute='_settings',
              new=config.Settings.construct(webdav_url='', webdav_username='', webdav_password=''))
def test_lang_detection2():
    lang_detector = get_lang_detector()
    text = 'London is the capital of Great Britain.'
    assert lang_detector.predict_lang(text) == 'en'


@patch.object(config,
              attribute='_settings',
              new=config.Settings.construct(webdav_url='', webdav_username='', webdav_password=''))
def test_lang_detection3():
    lang_detector = get_lang_detector()
    text = 'Лондон из зе кэпитал оф Грейт Британ!'
    assert lang_detector.predict_lang(text) == 'ru'


@patch.object(config,
              attribute='_settings',
              new=config.Settings.construct(webdav_url='', webdav_username='', webdav_password=''))
def test_lang_detection4():
    lang_detector = get_lang_detector()
    text = 'скажи що-небудь по-українськи'
    assert lang_detector.predict_lang(text) == 'uk'
