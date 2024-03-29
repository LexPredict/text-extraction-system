import re
from typing import Optional

# we instantiate this _ class instead of using load_model
# to avoid printing a useless warning coded in load_model
from fasttext.FastText import _FastText

from text_extraction_system.config import get_settings

TO_REMOVE = re.compile(r'\s+')


class FastTextLangDetector:

    def __init__(self):
        settings = get_settings()

        # we instantiate this _ class instead of using load_model
        # to avoid printing a useless warning coded in load_model
        self.model = _FastText(settings.fasttext_lang_model)

    def predict_lang(self, text: str):
        text = TO_REMOVE.sub(' ', text)
        detect_res = self.model.predict(text)
        label = detect_res[0][0]
        # the model returns labels in format: __label__en
        return label[9:]


_lang_detector: Optional[FastTextLangDetector] = None


def get_lang_detector():
    global _lang_detector
    if not _lang_detector:
        _lang_detector = FastTextLangDetector()
    return _lang_detector
