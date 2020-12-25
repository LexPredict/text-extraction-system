from typing import Optional

import fasttext

from text_extraction_system.config import get_settings


class FastTextLangDetector:

    def __init__(self):
        settings = get_settings()
        self.model = fasttext.load_model(settings.fasttext_lang_model)

    def predict_lang(self, text):
        detect_res = self.model.predict(text)
        label = detect_res[0][0]
        return label[9:]


_lang_detector: Optional[FastTextLangDetector] = None


def get_lang_detector():
    global _lang_detector
    if not _lang_detector:
        _lang_detector = FastTextLangDetector()
    return _lang_detector
