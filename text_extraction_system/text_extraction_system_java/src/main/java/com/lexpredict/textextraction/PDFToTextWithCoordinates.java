package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PageInfo;
import org.apache.pdfbox.cos.COSArray;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.PDPageTree;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDFont;
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
    int unmappedUnicodeCharsPerPage = 0;
    int totalCharsPerPage = 0;

    protected List<PageInfo> pages = new ArrayList<>();

    protected PageInfo curPage;

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
        this.curPage = new PageInfo();
        PDRectangle area = page.getMediaBox();
        this.curPage.box = new double[]{area.getLowerLeftX(), area.getLowerLeftY(),
                area.getWidth(), area.getHeight()};
        this.curPage.char_boxes = new ArrayList<>();
        this.output = new StringWriter();
    }

    @Override
    protected void endPage(PDPage page) throws IOException {
        writeParagraphEnd();
        totalCharsPerPage = 0;
        unmappedUnicodeCharsPerPage = 0;
        this.curPage.text = this.output.toString();
        this.pages.add(this.curPage);
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
    protected void showGlyph(Matrix textRenderingMatrix, PDFont font, int code, String unicode, Vector displacement) throws IOException {
        super.showGlyph(textRenderingMatrix, font, code, unicode, displacement);
        if (unicode == null || unicode.isEmpty()) {
            unmappedUnicodeCharsPerPage++;
        }
        totalCharsPerPage++;
    }

    @Override
    protected void writeString(String text, List<TextPosition> textPositions) throws IOException {
        super.writeString(text, textPositions);
        if (textPositions != null) {
            for (TextPosition pos : textPositions) {
                this.curPage.char_boxes.add(new double[]{pos.getX(), pos.getY(),
                        pos.getWidth(), pos.getHeight()});
            }
        }
    }

    protected void addNonPrintableCharBoxes(String nonPrintableText) {
        if (nonPrintableText != null && !nonPrintableText.isEmpty()) {
            for (int i = 0; i < nonPrintableText.length(); i++) {
                this.curPage.char_boxes.add(null);
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

    public static List<PageInfo> process(PDDocument document) throws Exception {
        return process(document, -1, Integer.MAX_VALUE);
    }

    public static List<PageInfo> process(PDDocument document, int startPage, int endPage) throws Exception {
        PDFToTextWithCoordinates pdf2text = new PDFToTextWithCoordinates();
        pdf2text.document = document;
        pdf2text.setStartPage(startPage);
        pdf2text.setEndPage(endPage);
        pdf2text.setAddMoreFormatting(true);
        pdf2text.setParagraphStart("\n");
        pdf2text.setSortByPosition(true);

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
        return pdf2text.pages;
    }

}
