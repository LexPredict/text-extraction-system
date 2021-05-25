package com.lexpredict.textextraction.dto;

/*
* Table of Contents reference
* */
public class PDFTOCRef {
    public String title;

    public double left, top;

    public int page;

    public PDFTOCRef() {
    }

    public PDFTOCRef(String title, double left, double top, int page) {
        this.title = title;
        this.left = left;
        this.top = top;
        this.page = page;
    }
}
