package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PDFPlainText;
import com.lexpredict.textextraction.dto.PDFPlainTextPage;
import org.apache.fontbox.util.BoundingBox;
import org.apache.pdfbox.cos.COSArray;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.PDPageTree;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDFont;
import org.apache.pdfbox.pdmodel.font.PDFontDescriptor;
import org.apache.pdfbox.pdmodel.font.PDTrueTypeFont;
import org.apache.pdfbox.pdmodel.font.PDType3Font;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDDocumentOutline;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineItem;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineNode;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import org.apache.pdfbox.util.Matrix;
import org.apache.pdfbox.util.Vector;
import org.xml.sax.SAXException;

import java.io.IOException;
import java.io.StringWriter;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Extracts plain text from PDF together with the bounding boxes of each page and character.
 * <p>
 * Based on the code from Apache TIKA and Apache PDFBox which
 * was originally licensed under Apache 2.0 license (https://tika.apache.org/license.html).
 */
public class PDFToTextWithCoordinates extends PDFTextStripper {
    int startPage = -1;
    int pageIndex = -1;

    protected List<PDFPlainTextPage> pages;

    protected List<double[]> charBBoxesWithPageNums;

    protected int curPageStartOffset;

    protected boolean enhancedSizeDetection = false;

    protected double r(double d) {
        BigDecimal bd = BigDecimal.valueOf(d);
        bd = bd.setScale(2, RoundingMode.HALF_UP);
        return bd.doubleValue();
    }

    protected PDFToTextWithCoordinates() throws IOException {
        super();
    }

    @Override
    protected void startDocument(PDDocument pdf) {
    }

    @Override
    protected void endDocument(PDDocument pdf) throws IOException {
        try {
            // Extract text for any bookmarks:
            extractBookmarkText();
        } catch (Exception e) {
            throw new IOException("Unable to end a document", e);
        }
    }

    @Override
    protected void startPage(PDPage page) throws IOException {
        super.startPage(page);
        this.curPageStartOffset = this.charBBoxesWithPageNums == null ? 0 : this.charBBoxesWithPageNums.size();
    }

    @Override
    protected void endPage(PDPage page) throws IOException {
        super.endPage(page);
        PDRectangle area = page.getMediaBox();
        PDFPlainTextPage pp = new PDFPlainTextPage();
        pp.bbox = new double[]{r(area.getLowerLeftX()), r(area.getLowerLeftY()),
                r(area.getWidth()), r(area.getHeight())};
        int curPageEndOffset = this.charBBoxesWithPageNums == null ? 0 : this.charBBoxesWithPageNums.size();
        pp.location = new int[] {this.curPageStartOffset, curPageEndOffset};
        this.pages.add(pp);
    }

    void extractBookmarkText() throws SAXException, IOException {
        PDDocumentOutline outline = document.getDocumentCatalog().getDocumentOutline();
        if (outline != null) {
            extractBookmarkText(outline);
        }
    }

    void extractBookmarkText(PDOutlineNode bookmark) {
        /*PDOutlineItem current = bookmark.getFirstChild();

        if (current != null) {
            xhtml.startElement("ul");
            while (current != null) {
                xhtml.startElement("li");
                xhtml.characters(current.getTitle());
                xhtml.endElement("li");
                handleDestinationOrAction(current.getAction(), AbstractPDF2XHTML.ActionTrigger.BOOKMARK);
                // Recurse:
                extractBookmarkText(current);
                current = current.getNextSibling();
            }
            xhtml.endElement("ul");
        }*/
    }

    /**
     * we need to override this because we are overriding {@link #processPages(PDPageTree)}
     *
     * @return
     */
    @Override
    public int getCurrentPageNo() {
        return pageIndex + 1;
    }

    /**
     * See TIKA-2845 for why we need to override this.
     *
     * @param pages
     * @throws IOException
     */
    @Override
    protected void processPages(PDPageTree pages) throws IOException {
        //we currently need this hack because we aren't able to increment
        //the private currentPageNo in PDFTextStripper,
        //and PDFTextStripper's processPage relies on that variable
        //being >= startPage when deciding whether or not to process a page
        // See:
        // if (currentPageNo >= startPage && currentPageNo <= endPage
        //                && (startBookmarkPageNumber == -1 || currentPageNo >= startBookmarkPageNumber)
        //                && (endBookmarkPageNumber == -1 || currentPageNo <= endBookmarkPageNumber))
        //        {
        super.setStartPage(-1);
        for (PDPage page : pages) {
            pageIndex++;
            if (getCurrentPageNo() >= getStartPage()
                    && getCurrentPageNo() <= getEndPage()) {
                processPage(page);
            }
        }
    }

    @Override
    public void setStartBookmark(PDOutlineItem pdOutlineItem) {
        throw new UnsupportedOperationException("We don't currently support this -- See PDFTextStripper's processPages() for how to implement this.");
    }

    @Override
    public void setEndBookmark(PDOutlineItem pdOutlineItem) {
        throw new UnsupportedOperationException("We don't currently support this -- See PDFTextStripper's processPages() for how to implement this.");
    }

    @Override
    public void setStartPage(int startPage) {
        this.startPage = startPage;
    }

    @Override
    public int getStartPage() {
        return startPage;
    }

    @Override
    protected void writeString(String text, List<TextPosition> textPositions) throws IOException {
        super.writeString(text, textPositions);
        if (textPositions != null) {
            for (TextPosition pos : textPositions) {
                double[] glyphBox = null;
                if (this.enhancedSizeDetection)
                    glyphBox = this.getEnhancedGlyphBox(pos);
                if (glyphBox == null)
                    glyphBox = new double[]{ getCurrentPageNo(), r(pos.getX()),
                            r(pos.getY()), r(pos.getWidth()), r(pos.getHeight())};

                this.charBBoxesWithPageNums.add(glyphBox);
            }
        }
    }

    protected double[] getEnhancedGlyphBox(TextPosition pos) throws IOException {
        PDFont font = pos.getFont();
        if (font == null)
            return null;

        PDFontDescriptor descr = font.getFontDescriptor();
        float fullHtAbs = (descr.getCapHeight()) / 1000 * pos.getFontSize();
        BoundingBox bbox = font.getBoundingBox();
        float fullHtRel = bbox.getHeight();
        float ascRel = descr.getAscent();
        float ascAbs = ascRel * fullHtAbs / fullHtRel;
        float capHtRel = descr.getCapHeight();
        float capHtAbs = capHtRel * fullHtAbs / fullHtRel;
        float y = pos.getY();
        y -= ascAbs;

        return new double[]{
                getCurrentPageNo(),
                r(pos.getX()), r(y),
                r(pos.getWidth()), r(capHtAbs)};
    }

    protected void addNonPrintableCharBoxes(String nonPrintableText) {
        if (nonPrintableText != null && !nonPrintableText.isEmpty()) {
            for (int i = 0; i < nonPrintableText.length(); i++) {
                this.charBBoxesWithPageNums.add(new double[] {getCurrentPageNo(), 0, 0, 0, 0});
            }
        }
    }

    @Override
    protected void writeLineSeparator() throws IOException {
        super.writeLineSeparator();
        this.addNonPrintableCharBoxes(getLineSeparator());
    }

    @Override
    protected void writeWordSeparator() throws IOException {
        super.writeWordSeparator();
        this.addNonPrintableCharBoxes(getWordSeparator());
    }

    @Override
    protected void writeParagraphStart() throws IOException {
        super.writeParagraphStart();
        this.addNonPrintableCharBoxes(getParagraphStart());
    }

    @Override
    protected void writeParagraphEnd() throws IOException {
        super.writeParagraphEnd();
        this.addNonPrintableCharBoxes(getParagraphEnd());
    }

    @Override
    protected void writePageStart() throws IOException {
        super.writePageStart();
        this.addNonPrintableCharBoxes(getPageStart());
    }

    @Override
    protected void writePageEnd() throws IOException {
        super.writePageEnd();
        this.addNonPrintableCharBoxes(getPageEnd());
    }

    @Override
    protected void endArticle() throws IOException {
        super.endArticle();
        this.addNonPrintableCharBoxes(getArticleEnd());
    }

    @Override
    protected void startArticle(boolean isLTR) throws IOException {
        super.startArticle(isLTR);
        this.addNonPrintableCharBoxes(getArticleStart());
    }


    static class AngleCollector extends PDFTextStripper {
        Set<Integer> angles = new HashSet<>();

        public Set<Integer> getAngles() {
            return angles;
        }

        AngleCollector() throws IOException {
        }

        @Override
        protected void processTextPosition(TextPosition text) {
            Matrix m = text.getTextMatrix();
            m.concatenate(text.getFont().getFontMatrix());
            int angle = (int) Math.round(Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY())));
            angle = (angle + 360) % 360;
            angles.add(angle);
        }
    }

    @Override
    public void processPage(PDPage page) throws IOException {
        //copied and pasted from https://issues.apache.org/jira/secure/attachment/12947452/ExtractAngledText.java
        //PDFBOX-4371
        AngleCollector angleCollector = new AngleCollector(); // alternatively, reset angles
        angleCollector.setStartPage(getCurrentPageNo());
        angleCollector.setEndPage(getCurrentPageNo());
        angleCollector.getText(document);

        int rotation = page.getRotation();
        page.setRotation(0);

        for (Integer angle : angleCollector.getAngles()) {
            if (angle == 0) {
                super.processPage(page);
            } else {
                // prepend a transformation
                try (PDPageContentStream cs = new PDPageContentStream(document,
                        page, PDPageContentStream.AppendMode.PREPEND, false)) {
                    cs.transform(Matrix.getRotateInstance(-Math.toRadians(angle), 0, 0));
                }
                super.processPage(page);
                // remove transformation
                COSArray contents = (COSArray) page.getCOSObject().getItem(COSName.CONTENTS);
                contents.remove(0);
            }
        }
        page.setRotation(rotation);
    }

    @Override
    protected void processTextPosition(TextPosition text) {
        Matrix m = text.getTextMatrix();
        m.concatenate(text.getFont().getFontMatrix());
        int angle = (int) Math.round(Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY())));
        if (angle == 0) {
            super.processTextPosition(text);
        }
    }

    public static PDFPlainText process(PDDocument document,
                                       boolean enhancedSizeDetection) throws Exception {
        return process(document, -1, Integer.MAX_VALUE, enhancedSizeDetection);
    }

    public static PDFPlainText process(PDDocument document,
                                       int startPage,
                                       int endPage,
                                       boolean enhancedSizeDetection) throws Exception {
        PDFToTextWithCoordinates pdf2text = new PDFToTextWithCoordinates();
        pdf2text.document = document;
        pdf2text.output = new StringWriter();
        pdf2text.charBBoxesWithPageNums = new ArrayList<>();
        pdf2text.pages = new ArrayList<>();
        pdf2text.setStartPage(startPage);
        pdf2text.setEndPage(endPage);
        pdf2text.setAddMoreFormatting(true);
        pdf2text.setParagraphEnd("\n");
        pdf2text.setPageEnd("\n\f");
        pdf2text.setSortByPosition(true);
        pdf2text.setShouldSeparateByBeads(true);
        pdf2text.enhancedSizeDetection = enhancedSizeDetection;

        // This prevents false-matches in paragraph detection
        // See TestPDF2Text.test_paragraphs()
        pdf2text.setDropThreshold(3f);

        //pdf2text.setPageStart(pdf2text.getLineSeparator());
        //pdf2text.setArticleStart(pdf2text.getLineSeparator());
        //pdf2text.setArticleEnd(pdf2text.getLineSeparator());
        //pdf2text.setIndentThreshold(1.5f);

        pdf2text.startDocument(document);
        pdf2text.processPages(document.getPages());
        pdf2text.endDocument(document);
        PDFPlainText res = new PDFPlainText();
        res.text = pdf2text.output.toString();
        res.pages = pdf2text.pages;
        res.charBBoxesWithPageNums = pdf2text.charBBoxesWithPageNums;
        return res;
    }
}
