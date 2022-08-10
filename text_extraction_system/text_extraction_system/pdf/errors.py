class ConvertToPDFFailed(Exception):
    pass


class OutputPDFDoesNotExistAfterConversion(ConvertToPDFFailed):
    pass


class InputFileDoesNotExist(ConvertToPDFFailed):
    pass
