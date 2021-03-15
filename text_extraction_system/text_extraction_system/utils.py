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
        try:
            language, locale_code = locale.replace('-', '_').split("_")[:2]
        except ValueError:
            language, locale_code = "", ""
        return language, locale_code
