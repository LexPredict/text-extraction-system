from contextlib import suppress
from os.path import abspath, splitext

import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException

DEFAULT_LIBREOFFICE_PORT = 2002
FAMILY_TEXT = "Text"
FAMILY_WEB = "Web"
FAMILY_SPREADSHEET = "Spreadsheet"
FAMILY_PRESENTATION = "Presentation"
FAMILY_DRAWING = "Drawing"

IMPORT_FILTER_MAP = {
    "txt": {
        "FilterName": "Text (encoded)",
        "FilterOptions": "utf8"
    },
    "csv": {
        "FilterName": "Text - txt - csv (StarCalc)",
        "FilterOptions": "44,34,0"
    }
}

# There is need in export to .pdf file only
EXPORT_FILTER_MAP = {
    "pdf": {
        FAMILY_TEXT: {"FilterName": "writer_pdf_Export"},
        FAMILY_WEB: {"FilterName": "writer_web_pdf_Export"},
        FAMILY_SPREADSHEET: {"FilterName": "calc_pdf_Export"},
        FAMILY_PRESENTATION: {"FilterName": "impress_pdf_Export"},
        FAMILY_DRAWING: {"FilterName": "draw_pdf_Export"}
    }
}

PAGE_STYLE_OVERRIDE_PROPERTIES = {
    FAMILY_SPREADSHEET: {
        "PageScale": 100,
        "PrintGrid": False
    }
}


class OfficeDocumentConverter:
    SUN_UNO_URL_RESOLVER = "com.sun.star.bridge.UnoUrlResolver"
    SUN_DESKTOP = "com.sun.star.frame.Desktop"
    SUN_WEB_DOCUMENT = "com.sun.star.text.WebDocument"
    SUN_GENERIC_TEXT_DOCUMENT = "com.sun.star.text.GenericTextDocument"
    SUN_SPREADSHEET_DOCUMENT = "com.sun.star.sheet.SpreadsheetDocument"
    SUN_PRESENTATION_DOCUMENT = "com.sun.star.presentation.PresentationDocument"
    SUN_DRAWING_DOCUMENT = "com.sun.star.drawing.DrawingDocument"

    def __init__(self, port=DEFAULT_LIBREOFFICE_PORT):
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(self.SUN_UNO_URL_RESOLVER,
                                                                          local_context)
        try:
            context = resolver.resolve(f"uno:socket,host=localhost,port={port};urp;"
                                       f"StarOffice.ComponentContext")
        except NoConnectException:
            raise Exception("failed to connect to LibreOffice on port %s" % port)
        self.desktop = context.ServiceManager.createInstanceWithContext(self.SUN_DESKTOP, context)

    def convert(self, input_file, output_file):
        input_url = uno.systemPathToFileUrl(abspath(input_file))
        output_url = uno.systemPathToFileUrl(abspath(output_file))
        load_properties = {"Hidden": True}
        input_ext = self._get_file_ext(input_file)
        output_ext = self._get_file_ext(output_file)
        if input_ext in IMPORT_FILTER_MAP:
            load_properties.update(IMPORT_FILTER_MAP[input_ext])

        document = self.desktop.loadComponentFromURL(input_url, "_blank", 0,
                                                     self._to_properties(load_properties))
        with suppress(AttributeError):
            document.refresh()

        family = self._detect_family(document)
        self._override_page_style_properties(document, family)

        try:
            properties_by_family = EXPORT_FILTER_MAP[output_ext]
        except KeyError:
            raise Exception("unknown output format: '%s'" % output_ext)

        family = self._detect_family(document)
        try:
            document.storeToURL(output_url, self._to_properties(properties_by_family[family]))
        except KeyError:
            raise Exception("unsupported conversion: from '%s' to '%s'" % (family, output_ext))
        finally:
            document.close(True)

    def _override_page_style_properties(self, document, family):
        if family in PAGE_STYLE_OVERRIDE_PROPERTIES:
            properties = PAGE_STYLE_OVERRIDE_PROPERTIES[family]
            page_styles = document.getStyleFamilies().getByName('PageStyles')
            for styleName in page_styles.getElementNames():
                page_style = page_styles.getByName(styleName)
                for name, value in list(properties.items()):
                    page_style.setPropertyValue(name, value)

    def _detect_family(self, document):
        if document.supportsService(self.SUN_WEB_DOCUMENT):
            return FAMILY_WEB
        if document.supportsService(self.SUN_GENERIC_TEXT_DOCUMENT):
            return FAMILY_TEXT
        if document.supportsService(self.SUN_SPREADSHEET_DOCUMENT):
            return FAMILY_SPREADSHEET
        if document.supportsService(self.SUN_PRESENTATION_DOCUMENT):
            return FAMILY_PRESENTATION
        if document.supportsService(self.SUN_DRAWING_DOCUMENT):
            return FAMILY_DRAWING
        raise Exception("unknown document family: %s" % document)

    def _get_file_ext(self, path):
        ext = splitext(path)[1]
        return ext[1:].lower() if ext else ""

    def _to_properties(self, dictionary):
        props = []
        for key in dictionary:
            prop = PropertyValue()
            prop.Name = key
            prop.Value = dictionary[key]
            props.append(prop)
        return tuple(props)
