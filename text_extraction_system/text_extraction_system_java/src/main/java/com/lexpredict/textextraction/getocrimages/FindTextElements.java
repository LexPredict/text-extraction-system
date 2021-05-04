package com.lexpredict.textextraction.getocrimages;

import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import org.apache.pdfbox.util.Matrix;

import java.awt.geom.Rectangle2D;
import java.io.IOException;
import java.io.StringWriter;
import java.util.LinkedList;
import java.util.List;

public class FindTextElements extends PDFTextStripper {

    public FindTextElements() throws IOException {
        this.setStartPage(-1);
        this.output = new StringWriter();
    }

    public static class FoundTextElement {
        public final Rectangle2D.Float bounds;


        public FoundTextElement(Rectangle2D.Float bounds) {
            this.bounds = bounds;
        }
    }

    public List<FoundTextElement> found = new LinkedList<>();

    @Override
    protected void processTextPosition(TextPosition pos) {
        Matrix tm = pos.getTextMatrix();
        Rectangle2D.Float bounds = new Rectangle2D.Float(tm.getTranslateX(),
                tm.getTranslateY(), pos.getWidth(), pos.getHeight());
        this.found.add(new FoundTextElement(bounds));

    }
}
