package com.lexpredict.textextraction.dto;

public class PDFPlainTextPage {

    public double[] bbox;

    public int[] location;

    public double deskewAngle;

    public PDFPlainTextPage() {
    }

    public PDFPlainTextPage(double[] bbox, int[] location, double deskewAngle) {
        this.bbox = bbox;
        this.location = location;
        this.deskewAngle = deskewAngle;
    }
}
