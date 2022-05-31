package com.lexpredict.textextraction.errors;

public class InjuredDocumentException extends Exception {
    public InjuredDocumentException() {
        super("The document is injured and cannot be processed");
    }

    public InjuredDocumentException(String errorMessage) {
        super(errorMessage);
    }
}
