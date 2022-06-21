package com.lexpredict.textextraction.getocrimages;

import com.lexpredict.textextraction.TEUtils;
import com.lexpredict.textextraction.dto.PDFVisibleTextStripper;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.text.TextPosition;
import org.apache.pdfbox.util.Matrix;

import java.awt.geom.Rectangle2D;
import java.io.IOException;
import java.io.StringWriter;
import java.util.LinkedList;
import java.util.List;

public class FindTextElements extends PDFVisibleTextStripper {

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
        if (!TEUtils.containsAlphaNumeric(pos.getUnicode()))
            return;
        Matrix tm = pos.getTextMatrix();
        Rectangle2D.Float bounds = new Rectangle2D.Float(tm.getTranslateX(),
                tm.getTranslateY(), pos.getWidth(), pos.getHeight());
        this.found.add(new FoundTextElement(bounds));

    }
}
