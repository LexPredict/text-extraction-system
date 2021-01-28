package com.lexpredict.textextraction.dto;

public class PDFPlainTextPage {

    public double[] bbox;

    public int[] location;

    public PDFPlainTextPage() {
    }

    public PDFPlainTextPage(double[] bbox, int[] location) {
        this.bbox = bbox;
        this.location = location;
    }
}
