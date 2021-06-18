package com.lexpredict.textextraction.dto;

/*
* Table of Contents reference
* */
public class PDFTOCRef {
    public String title;

    public int level;

    public double left, top;

    public int page;

    public PDFTOCRef() {
    }

    public PDFTOCRef(String title, int level, double left, double top, int page) {
        this.title = title;
        this.level = level;
        this.left = left;
        this.top = top;
        this.page = page;
    }

    @Override
    public String toString() {
        return "PDFTOCRef{" +
                "title='" + title + '\'' +
                ", level=" + level +
                ", left=" + left +
                ", top=" + top +
                ", page=" + page +
                '}';
    }
}
