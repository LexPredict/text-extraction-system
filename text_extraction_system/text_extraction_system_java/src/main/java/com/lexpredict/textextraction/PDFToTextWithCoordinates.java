package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PDFPlainText;
import com.lexpredict.textextraction.dto.PDFPlainTextPage;
import org.apache.pdfbox.cos.COSArray;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.PDPageTree;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDDocumentOutline;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineItem;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineNode;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import org.apache.pdfbox.util.Matrix;
import org.xml.sax.SAXException;

import java.awt.geom.Rectangle2D;
import java.io.IOException;
import java.io.StringWriter;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

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

    protected List<double[]> charBBoxes;

    protected int curPageStartOffset;

    protected boolean insideInternalPageProcessing = false;

    protected boolean deskew;

    protected int maxDeskewAngleAbs = 4;

    protected Matrix curCharBackTransform;

    protected double curAngle;

    protected boolean removeNonPrintable = false;

    protected int ignoreAnglesCloserThan = 3;

    protected boolean detectAngles = false;

    private double[] curAngleLimits = null;

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
        this.curPageStartOffset = this.charBBoxes == null ? 0 : this.charBBoxes.size();
    }

    @Override
    protected void endPage(PDPage page) throws IOException {
        super.endPage(page);
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
        if (textPositions == null)
            return;

        StringBuilder sb = new StringBuilder();
        for (TextPosition pos : textPositions) {

            double[] glyphBox = new double[]{r(pos.getX()),
                    r(pos.getY()), r(pos.getWidth()), r(pos.getHeight())};
            String unicode = pos.getUnicode();

            if (removeNonPrintable && (glyphBox[2] == 0 || glyphBox[3] == 0))
                continue;

            restoreAngle(glyphBox);

            for (int i = 0; i < unicode.length(); i++)
                this.charBBoxes.add(glyphBox);

            sb.append(unicode);
        }
        super.writeString(sb.toString(), textPositions);
    }

    protected void restoreAngle(double[] bbox) {

        if (this.curCharBackTransform != null) {
            PDRectangle r = new PDRectangle((float) bbox[0], (float) bbox[1], (float) bbox[2], (float) bbox[3]);
            Rectangle2D r1 = r.transform(this.curCharBackTransform).getBounds2D();
            bbox[0] = r1.getX();
            bbox[1] = r1.getY();
            bbox[2] = r1.getWidth();
            bbox[3] = r1.getHeight();

            double a = Math.abs(this.curAngle);
            a = a <= 180 ? a : 360 - a;
            double b = this.curAngle;
            b = b <= -90 ? -180 - b
                    : b <= 0 ? b
                    : b <= 90 ? b
                    : 180 - b;


            bbox[1] += bbox[3] * 2 * (a / 180);
            bbox[0] += bbox[2] * (b / 90);
        }

    }

    protected void addNonPrintableCharBoxes(String nonPrintableText) {
        if (nonPrintableText != null && !nonPrintableText.isEmpty()) {
            for (int i = 0; i < nonPrintableText.length(); i++) {
                this.charBBoxes.add(new double[]{0, 0, 0, 0});
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
        if (this.insideInternalPageProcessing)
            return;
        super.writePageStart();
        this.addNonPrintableCharBoxes(getPageStart());
    }

    @Override
    protected void writePageEnd() throws IOException {
        if (this.insideInternalPageProcessing)
            return;
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

    protected static double normAngle(double angle) {
        angle = angle % 360;
        angle = angle > 180 ? angle - 360 : angle;
        return angle;
    }

    static class AngleCollector extends PDFTextStripper {
        Map<Integer, Integer> anglesToCharNum = new HashMap<>();

        final int ignoreAnglesCloserThan;

        int[] sortedAngles;

        AngleCollector(int ignoreAnglesCloserThan) throws IOException {
            this.ignoreAnglesCloserThan = ignoreAnglesCloserThan;
        }

        public void cleanupAngles() {
            Map<Integer, Integer> res = new HashMap<>();

            List<Map.Entry<Integer, Integer>> anglesToCharNumSorted = new ArrayList<>(this.anglesToCharNum.entrySet());
            anglesToCharNumSorted.sort(Map.Entry.<Integer, Integer>comparingByValue().reversed());

            for (Map.Entry<Integer, Integer> angleNum : anglesToCharNumSorted) {
                Integer closestAngle = null;
                Integer closestAngleCharNum = null;
                for (Map.Entry<Integer, Integer> angleNum2 : res.entrySet()) {
                    int phi = Math.abs(angleNum.getKey() - angleNum2.getKey()) % 360;
                    int distance = phi > 180 ? 360 - phi : phi;
                    if (distance < ignoreAnglesCloserThan) {
                        closestAngle = angleNum2.getKey();
                        closestAngleCharNum = angleNum2.getValue();
                    }
                }

                if (closestAngle != null) {
                    res.put(closestAngle, closestAngleCharNum + angleNum.getValue());
                } else {
                    res.put(angleNum.getKey(), angleNum.getValue());
                }
            }

            List<Map.Entry<Integer, Integer>> entries = new ArrayList<>(res.entrySet());
            entries.sort(Map.Entry.comparingByValue());

            int[] sortedAngles = new int[entries.size()];
            int i = 0;
            for (Map.Entry<Integer, Integer> e : entries) {
                sortedAngles[i] = e.getKey();
                i++;
            }
            this.sortedAngles = sortedAngles;
        }

        public void inc(int rotationAngle) {
            Map<Integer, Integer> anglesToCharNum = new HashMap<>();
            for (Map.Entry<Integer, Integer> e : this.anglesToCharNum.entrySet()) {
                anglesToCharNum.put(e.getKey() + rotationAngle, e.getValue());
            }
            this.anglesToCharNum = anglesToCharNum;
            for (int i = 0; i < sortedAngles.length; i++) {
                sortedAngles[i] += rotationAngle;
            }
        }

        public double[] getLimitsByAngle(int angle) {
            Integer closestLeft = null;
            Integer closestRight = null;
            for (int angle1 : this.sortedAngles) {
                if (angle1 < angle && (closestLeft == null || angle1 > closestLeft))
                    closestLeft = angle1;
                else if (angle1 > angle && (closestRight == null || angle1 < closestRight))
                    closestRight = angle1;
            }

            double limitLeft = closestLeft != null ? -((double) angle - closestLeft) / 2 : -ignoreAnglesCloserThan;
            double limitRight = closestRight != null ? ((double) closestRight - angle) / 2 : +ignoreAnglesCloserThan;

            return new double[]{limitLeft, limitRight};

        }

        @Override
        protected void processTextPosition(TextPosition text) {
            Matrix m = text.getTextMatrix();
            m.concatenate(text.getFont().getFontMatrix());
            double angle = Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY()));
            angle = normAngle(angle);
            // do we need the proper float angle auto-clustering here?
            anglesToCharNum.merge((int) Math.round(angle), text.getCharacterCodes().length, Integer::sum);
        }

        protected int[] selectDeskewAngle(int skewAngleAbsLimit) {
            if (sortedAngles == null || sortedAngles.length == 0) {
                return new int[] {0, 0, 0};
            }

            for (int i = this.sortedAngles.length - 1; i >= 0; i--) {
                int angle = sortedAngles[i];
                int pageRotation = 90 * Math.round((float) angle / 90);
                int skewAngle = angle - pageRotation;
                if (Math.abs(skewAngle) <= Math.abs(skewAngleAbsLimit))
                    return new int[]{angle, pageRotation, skewAngle};
            }

            int angle = sortedAngles[this.sortedAngles.length - 1];
            int pageRotation = 90 * Math.round((float) angle / 90);
            int skewAngle = 0;
            return new int[]{angle, pageRotation, skewAngle};
        }
    }

    protected Matrix rotateMatrix(PDRectangle cropBox, int angle) {
        float tx = (cropBox.getLowerLeftX() + cropBox.getUpperRightX()) / 2;
        float ty = (cropBox.getLowerLeftY() + cropBox.getUpperRightY()) / 2;
        Matrix m = Matrix.getTranslateInstance(tx, ty);
        m.concatenate(Matrix.getRotateInstance(Math.toRadians(angle), 0, 0));
        m.concatenate(Matrix.getTranslateInstance(-tx, -ty));
        return m;
    }


    @Override
    public void processPage(PDPage page) throws IOException {
        int pageStart = this.charBBoxes == null ? 0 : this.charBBoxes.size();
        int deskewFullAngle = 0;

        if (this.detectAngles) {
            int oldRotation = page.getRotation();
            page.setRotation(0);
            AngleCollector angleCollector = new AngleCollector(this.ignoreAnglesCloserThan);
            angleCollector.setStartPage(getCurrentPageNo());
            angleCollector.setEndPage(getCurrentPageNo());
            angleCollector.getText(document);
            angleCollector.cleanupAngles();


            int[] deskewFullAngleRotationSkewAngle = angleCollector.selectDeskewAngle(this.maxDeskewAngleAbs);
            deskewFullAngle = deskewFullAngleRotationSkewAngle[0];
            int deskewPageRotation = deskewFullAngleRotationSkewAngle[1];
            int deskewSkewAngle = deskewFullAngleRotationSkewAngle[2];
            this.writePageStart();
            this.insideInternalPageProcessing = true;
            for (Integer angle : angleCollector.sortedAngles) {
                this.curAngleLimits = angleCollector.getLimitsByAngle(angle);
                this.curCharBackTransform = null;
                this.curAngle = 0;
                if (angle != 0) {
                    Matrix curAngleMatrix = rotateMatrix(page.getCropBox(), -angle);
                    try (PDPageContentStream cs = new PDPageContentStream(document,
                            page, PDPageContentStream.AppendMode.PREPEND, false)) {
                        cs.transform(curAngleMatrix);
                    }

                    Matrix charRestoreMatrix = null;
                    if (deskew) {
                        charRestoreMatrix = rotateMatrix(page.getCropBox(), -angle + deskewSkewAngle);
                    } else {
                        charRestoreMatrix = rotateMatrix(page.getCropBox(), -angle);
                    }


                    this.curCharBackTransform = charRestoreMatrix;
                    this.curAngle = -angle;
                    super.processPage(page);
                    ((COSArray) page.getCOSObject().getItem(COSName.CONTENTS)).remove(0);
                } else {
                    super.processPage(page);
                }
                this.curAngleLimits = null;
            }
            this.insideInternalPageProcessing = false;
            this.writePageEnd();

            if (deskew) {
                page.setRotation(deskewPageRotation);
                if (deskewSkewAngle != 0) {
                    try (PDPageContentStream cs = new PDPageContentStream(document,
                            page, PDPageContentStream.AppendMode.PREPEND, false)) {

                        cs.transform(rotateMatrix(page.getCropBox(), -deskewSkewAngle));
                    }
                }
            } else {
                page.setRotation(oldRotation);
            }
        } else {
            super.processPage(page);
        }

        PDRectangle area = page.getMediaBox();
        PDFPlainTextPage pp = new PDFPlainTextPage();
        pp.bbox = new double[]{
                r(area.getLowerLeftX()), r(area.getLowerLeftY()),
                r(area.getWidth()), r(area.getHeight())};
        int pageEnd = this.charBBoxes == null ? 0 : this.charBBoxes.size();
        pp.location = new int[]{pageStart, pageEnd};
        pp.deskewAngle = (double) deskewFullAngle;
        this.pages.add(pp);
    }

    @Override
    protected void processTextPosition(TextPosition text) {
        if (!this.detectAngles) {
            super.processTextPosition(text);
            return;
        }
        Matrix m = text.getTextMatrix();
        m.concatenate(text.getFont().getFontMatrix());
        double angle = normAngle(Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY())));

        if (angle >= this.curAngleLimits[0] && angle < this.curAngleLimits[1])
            super.processTextPosition(text);
    }

    public static PDFPlainText process(PDDocument document, boolean deskew) throws Exception {
        return process(document, -1, Integer.MAX_VALUE, deskew);
    }

    public static PDFPlainText process(PDDocument document,
                                       int startPage,
                                       int endPage,
                                       boolean deskew) throws Exception {
        PDFToTextWithCoordinates pdf2text = new PDFToTextWithCoordinates();
        pdf2text.document = document;
        pdf2text.deskew = deskew;
        pdf2text.output = new StringWriter();
        pdf2text.charBBoxes = new ArrayList<>();
        pdf2text.pages = new ArrayList<>();
        pdf2text.setStartPage(startPage);
        pdf2text.detectAngles = true;
        pdf2text.maxDeskewAngleAbs = 4;
        pdf2text.setEndPage(endPage);
        pdf2text.setAddMoreFormatting(true);
        pdf2text.setParagraphEnd("\n");
        pdf2text.setPageEnd("\n\f");

        // Setting to true breaks multi-column layouts
        // Setting to false breaks complicated diagrams
        pdf2text.setSortByPosition(false);

        pdf2text.setShouldSeparateByBeads(true);
        pdf2text.removeNonPrintable = true;

        // This prevents false-matches in paragraph detection
        // See TestPDF2Text.test_paragraphs()
        pdf2text.setDropThreshold(3.5f);

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
        res.charBBoxes = pdf2text.charBBoxes;
        return res;
    }
}
