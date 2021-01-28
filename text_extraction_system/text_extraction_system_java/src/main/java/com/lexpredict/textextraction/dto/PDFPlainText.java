package com.lexpredict.textextraction.dto;

import java.util.List;

public class PDFPlainText {

    public String text;

    public List<double[]> charBBoxesWithPageNums;

    public List<PDFPlainTextPage> pages;

}
