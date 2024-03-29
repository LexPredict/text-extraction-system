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
import java.util.*;

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

    protected int maxDeskewAngleAbs = 7;

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
                try {
                    processPage(page);
                } catch (IOException e){}
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

            Matrix tm = pos.getTextMatrix();
            double[] glyphBox = new double[]{r(tm.getTranslateX()),
                    r(tm.getTranslateY()), r(pos.getWidth()), r(pos.getHeight())};
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
        Map<Float, Integer> anglesToCharNum = new HashMap<>();

        final int ignoreAnglesCloserThan;

        float[] sortedAngles;

        private int rShifts = 0, lShifts = 0, dShifts = 0, uShifts = 0;

        private float lastX = -1, lastY = -1;

        AngleCollector(int ignoreAnglesCloserThan) throws IOException {
            this.ignoreAnglesCloserThan = ignoreAnglesCloserThan;
        }

        public void cleanupAngles() {
            Map<Float, Integer> res = new HashMap<>();

            List<Map.Entry<Float, Integer>> anglesToCharNumSorted = new ArrayList<>(this.anglesToCharNum.entrySet());
            anglesToCharNumSorted.sort(Map.Entry.<Float, Integer>comparingByValue().reversed());

            for (Map.Entry<Float, Integer> angleNum : anglesToCharNumSorted) {
                Float closestAngle = null;
                Integer closestAngleCharNum = null;
                for (Map.Entry<Float, Integer> angleNum2 : res.entrySet()) {
                    Float phi = Math.abs(angleNum.getKey() - angleNum2.getKey()) % 360;
                    Float distance = phi > 180 ? 360 - phi : phi;
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

            List<Map.Entry<Float, Integer>> entries = new ArrayList<>(res.entrySet());
            entries.sort(Map.Entry.comparingByValue());

            float[] sortedAngles = new float[entries.size()];
            int i = 0;
            for (Map.Entry<Float, Integer> e : entries) {
                sortedAngles[i] = e.getKey();
                i++;
            }
            this.sortedAngles = sortedAngles;
        }

        public double[] getLimitsByAngle(float angle) {
            Float closestLeft = null;
            Float closestRight = null;
            for (float angle1 : this.sortedAngles) {
                if (angle1 < angle && (closestLeft == null || angle1 > closestLeft))
                    closestLeft = angle1;
                else if (angle1 > angle && (closestRight == null || angle1 < closestRight))
                    closestRight = angle1;
            }

            double limitLeft = closestLeft != null ? -((double) angle - closestLeft) / 2 : -ignoreAnglesCloserThan;
            double limitRight = closestRight != null ? ((double) closestRight - angle) / 2 : +ignoreAnglesCloserThan;

            return new double[]{limitLeft, limitRight};

        }

        public int getAngleByTrend() {
            if (rShifts + lShifts + dShifts + uShifts < 40)
                return 0;  // too less data to determine trends
            // l >> r, d > u, d > l => page is rotated 90 CW
            if ((lShifts > 4 * rShifts) &&
                (dShifts > uShifts * 2)
                /*(dShifts > lShifts)*/) return 90;
            // r >> l, u > d, u > r => page is rotated 90 CCW
            if ((rShifts > 4 * lShifts) &&
                (uShifts > dShifts * 2)
                /*(uShifts > rShifts)*/) return -90;
            // u >> d, l > r, l > u => page is rotated 180 CW
            if ((uShifts > 4 * dShifts) &&
                (lShifts > rShifts * 2)
                /*(lShifts > uShifts)*/) return 180;
            return 0;
        }

        @Override
        protected void processTextPosition(TextPosition text) {
            if (!TEUtils.containsAlphaNumeric(text.getUnicode()))
                return;
            float x = text.getX(), y = text.getY();
            if (lastX != -1 && lastY != -1) {
                if (x > lastX)
                    rShifts++;
                else if (x < lastX)
                    lShifts++;
                if (y > lastY)
                    dShifts++;
                else if (y < lastY)
                    uShifts++;
            }
            lastX = x;
            lastY = y;

            Matrix m = text.getTextMatrix();
            m.concatenate(text.getFont().getFontMatrix());
            double angle = Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY()));
            angle = normAngle(angle);
            // do we need the proper float angle auto-clustering here?
            anglesToCharNum.merge(Math.round(angle * 10) / 10f, text.getCharacterCodes().length, Integer::sum);
        }

        protected float getWeightedModAngle() {
            // maximum standard deviation of detected char angles
            // if angles distribution has "long tails" we believe the angles detected
            // aren't representative. NB: this constant is measured in degrees
            final int minCountToStrip = 2;
            float tailSkipQuantile = 0.1f;

            WeightedCharAngle[] wAngles = new WeightedCharAngle[this.anglesToCharNum.size()];
            int i = 0, totalCount = 0;
            for (Map.Entry<Float, Integer> entry : this.anglesToCharNum.entrySet()) {
                float angle = entry.getKey();
                int count = entry.getValue();
                totalCount += count;
                wAngles[i++] = new WeightedCharAngle(angle, count, 0);
            }
            if (totalCount == 0)
                return 0;

            // calculate distances between angle value / average angle value (totalAverage)
            // we'll use the distances for cutting head and tail quantiles of extreme distant values
            float totalAverage = Arrays.stream(wAngles).map(it -> it.angle * it.count).reduce(0f, Float::sum);
            totalAverage /= totalCount;
            for (WeightedCharAngle w: wAngles)
                w.distance = Math.abs(w.angle - totalAverage);

            if (this.anglesToCharNum.size() < minCountToStrip)
                tailSkipQuantile = 0;

            // remove up to 10% (0.1f) values that are too far from avgAngle
            float[] angleDev = WeightedCharAngle.getWeightedAverage(wAngles, tailSkipQuantile);
            float avgAngle = Math.round(angleDev[0] * 10) / 10F;
            if (!WeightedCharAngle.checkStandardDeviationOk(avgAngle, angleDev[1]))
                return 0;
            return avgAngle;
        }

        protected float[] selectDeskewAngle(int skewAngleAbsLimit) {
            if (sortedAngles == null || sortedAngles.length == 0) {
                return new float[]{0, 0, 0};
            }

            float angle = getWeightedModAngle();

            int pageRotation = 90 * Math.round(angle / 90);
            float skewAngle = angle - pageRotation;
            if (Math.abs(skewAngle) <= skewAngleAbsLimit)
                return new float[]{angle, pageRotation, skewAngle};

            pageRotation = 90 * Math.round(angle / 90F);
            skewAngle = 0;

            // [ avg_angle, avg_angle ~ 90, avg_angle - (avg_angle ~ 90) ]
            return new float[]{angle, pageRotation, skewAngle};
        }
    }

    protected Matrix rotateMatrix(PDRectangle cropBox, float angle) {
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
        float deskewFullAngle = 0;

        if (this.detectAngles) {
            int oldRotation = page.getRotation();
            page.setRotation(0);
            AngleCollector angleCollector = new AngleCollector(this.ignoreAnglesCloserThan);
            angleCollector.setStartPage(getCurrentPageNo());
            angleCollector.setEndPage(getCurrentPageNo());
            angleCollector.getText(document);
            angleCollector.cleanupAngles();

            // [ avg_angle, avg_angle ~ 90, avg_angle - (avg_angle ~ 90) ]
            float[] deskewFullAngleRotationSkewAngle = angleCollector.selectDeskewAngle(this.maxDeskewAngleAbs);
            deskewFullAngle = deskewFullAngleRotationSkewAngle[0];
            float deskewPageRotation = deskewFullAngleRotationSkewAngle[1];
            float deskewSkewAngle = deskewFullAngleRotationSkewAngle[2];
            this.writePageStart();
            this.insideInternalPageProcessing = true;
            for (int ia = angleCollector.sortedAngles.length - 1; ia >= 0; ia--) {
                float angle = angleCollector.sortedAngles[ia];
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
                        charRestoreMatrix = rotateMatrix(page.getCropBox(), angle - deskewSkewAngle);
                    } else {
                        charRestoreMatrix = rotateMatrix(page.getCropBox(), angle);
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
                if (deskewPageRotation != 0 || oldRotation != 0 || deskewSkewAngle != 0)
                    System.out.println(String.format("%d] deskewPageRotation=%.2f, oldRotation=%d, deskewSkewAngle=%.2f",
                        this.pageIndex, deskewPageRotation, oldRotation, deskewSkewAngle));
                if (Math.round(deskewPageRotation) != 0)
                    page.setRotation(Math.round(deskewPageRotation));
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
        PDFPlainText data = process(document, -1, Integer.MAX_VALUE, deskew);
        data.tableOfContents = GetTOCFromPDF.getTableOfContents(document);
        return data;
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
        pdf2text.maxDeskewAngleAbs = 8;
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