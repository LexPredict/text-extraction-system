from text_extraction_system.constants import TESSERACT_LANGUAGES, TESSERACT_DEFAULT_LANGUAGE


class LanguageConverter:
    @staticmethod
    def convert_language_to_tesseract_view(language: str):
        """
        Converts short 2-letters language code to proper tesseract language representation.
        If tesseract doesn't support language, then use default tesseract language
        """
        return TESSERACT_LANGUAGES.get(language, TESSERACT_DEFAULT_LANGUAGE)

    @staticmethod
    def get_language_and_locale_code(locale: str):
        """
        Extracts language and locale code from locale representation
        """
        data = locale.replace('-', '_').split("_")[:2]
        if len(data) < 2:
            data.append("")
        language, locale_code = data
        return language, locale_code


def page_num_to_fn(page_num: int) -> str:
    return f'{page_num:05}'
