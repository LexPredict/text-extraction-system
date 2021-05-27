package com.lexpredict.textextraction.dto;

import java.util.List;

public class PDFPlainText {

    public String text;

    public List<double[]> charBBoxes;

    public List<PDFPlainTextPage> pages;

    public List<PDFTOCRef> tableOfContents;
}
