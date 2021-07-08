package com.lexpredict.textextraction.mergepdf;

import org.apache.commons.cli.*;
import org.apache.commons.io.FilenameUtils;
import org.apache.pdfbox.multipdf.LayerUtility;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.graphics.form.PDFormXObject;
import org.apache.pdfbox.util.Matrix;

import java.awt.*;
import java.awt.geom.AffineTransform;
import java.io.File;
import java.io.FileFilter;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Merges specified PDF pages into the original PDF as layers in front of the original page content.
 * May be used to put the results of the pages OCR by Tesseract in front of the pages keeping the original PDF
 * structure and annotations and small PDF size.
 * <p>
 * Workflow:
 * 1. Figure out if a PDF page requires OCR or not. If yes, then:
 * 2. Generate an image of a PDF page with the existing text elements removed and only the image elements left.
 * See GetOCRImages class.
 * 3. Execute Tesseract on the page image specifying it to return the text-only PDF with the transparent
 * glyph-less text and no image background.
 * 4. Merge the transparent glyph-less text into the original PDF putting it in front of the page data
 * using this class.
 * <p>
 * The original bookmarks and the structure of the PDF is kept, the original text elements are left untouched
 * and in front of the original image elements there will be the glyph-less text layer generated by OCR.
 */
public class MergeInPageLayers {
    static class PageAngle {
        public int page;
        public double angle;
    }

    private static final String EXT_PDF = ".pdf";

    private static final Pattern PAGE_NUM_FN = Pattern.compile("^(\\d+)=(.*)$");

    private static final Pattern PAGE_ROTATE_ANGLE = Pattern.compile("^rotate_(\\d+)=(.*)$");

    public static void main(String[] args) throws IOException {

        CommandLine cmd = parseCliArgs(args);

        String pdf = cmd.getOptionValue("original-pdf");
        String pagesDirStr = cmd.getOptionValue("page-dir", null);
        String password = cmd.getOptionValue("password");
        String dstPdf = cmd.getOptionValue("dst-pdf");

        Map<Integer, File> pageToFn = new HashMap<>();
        Map<Integer, Double> pageRotateAngles = new HashMap<>();

        System.out.println("MergeInPageLayers is called");

        if (pagesDirStr != null) {
            File pagesDir = new File(pagesDirStr);
            File[] pageFiles = pagesDir.listFiles(new FileFilter() {
                @Override
                public boolean accept(File pathname) {
                    return pathname.getName().endsWith(EXT_PDF);
                }
            });

            if (pageFiles == null) {
                System.out.println("Page directory is invalid:\n" + pagesDirStr);
                return;
            }

            for (File fn : pageFiles) {
                try {
                    PageAngle pa = getPageAndAngleFromFileName(fn.getName());
                    pageToFn.put(pa.page, fn);
                    if (pa.angle != 0)
                        pageRotateAngles.put(pa.page, pa.angle);
                } catch (NumberFormatException nfe) {
                    System.out.println("Unable to parse page file name: " + fn.getName() + ".\n" +
                            "Expected format: <page_num>.<rotate_angle>.pdf or <page_num>.pdf");
                }
            }

            if (pageToFn.isEmpty()) {
                System.out.println("Page directory does not contain page files named [int_page_num].pdf\n" + pagesDirStr);
            }
        }

        // Fill page file names and rotate angles from command line args
        for (String arg : cmd.getArgList()) {
            Matcher m = PAGE_NUM_FN.matcher(arg);
            if (m.find()) {
                int pageNum = Integer.parseInt(m.group(1));
                String pageFn = m.group(2);
                pageToFn.put(pageNum, new File(pageFn));
            }

            Matcher m1 = PAGE_ROTATE_ANGLE.matcher(arg);
            if (m1.find()) {
                int pageNum = Integer.parseInt(m1.group(1));
                String angleStr = m1.group(2);
                pageRotateAngles.put(pageNum, Double.parseDouble(angleStr));
            }
        }

        try (PDDocument dstDocument = PDDocument.load(new File(pdf), password)) {
            LayerUtility layerUtility = new LayerUtility(dstDocument);
            for (Map.Entry<Integer, File> pageFn : pageToFn.entrySet()) {
                int pageNumZeroBased = pageFn.getKey() - 1;
                PDPage dstPage = dstDocument.getPage(pageNumZeroBased);
                try (PDDocument layerDocument = PDDocument.load(pageFn.getValue(), (String) null)) {
                    PDPage layerPage = layerDocument.getPage(0);
                    PDRectangle layerCropBox = layerPage.getCropBox();
                    PDRectangle dstCropBox = dstPage.getCropBox();

                    AffineTransform insertTransform = new AffineTransform();
                    float origW = dstCropBox.getUpperRightX();
                    float layerW = layerCropBox.getUpperRightX();
                    if (layerW > 0) {
                        float k = origW / layerW;
                        insertTransform.concatenate(AffineTransform.getScaleInstance(k, k));
                        layerCropBox = dstCropBox;
                    }
                    int dstRotate = dstPage.getRotation();

                    if (dstRotate != 0) {
                        double tx = (layerCropBox.getLowerLeftX() + layerCropBox.getUpperRightX()) / 2;
                        double ty = (layerCropBox.getLowerLeftY() + layerCropBox.getUpperRightY()) / 2;
                        double tx1 = (dstCropBox.getLowerLeftX() + dstCropBox.getUpperRightX()) / 2;
                        double ty1 = (dstCropBox.getLowerLeftY() + dstCropBox.getUpperRightY()) / 2;

                        insertTransform.concatenate(AffineTransform.getTranslateInstance(tx1, ty1));
                        insertTransform.concatenate(AffineTransform.getRotateInstance(Math.toRadians(dstRotate)));
                        insertTransform.concatenate(AffineTransform.getTranslateInstance(-tx, -ty));
                    }

                    // Rotate original page if requested
                    // TODO: Not sure if this really works after rotating the layer being inserted (see above)
                    Double rotate = pageRotateAngles.get(pageFn.getKey());

                    if (rotate != null) {
                        int pageRotate = -90 * (int) Math.round(rotate / 90d);
                        double contentsRotate = rotate + pageRotate;

                        pageRotate += dstRotate;

                        dstPage.setRotation(pageRotate);
                        rotatePageContents(dstDocument, dstPage, contentsRotate);
                    }

                    PDFormXObject layerForm = layerUtility.importPageAsForm(layerDocument, 0);
                    layerUtility.wrapInSaveRestore(dstPage);

                    int i = 0;
                    boolean done = false;

                    while (!done) {
                        try {
                            layerUtility.appendFormAsLayer(dstPage, layerForm, insertTransform,
                                    "Recognized Text for Page " + pageFn.getKey() + " " + i);
                            done = true;
                        } catch (IllegalArgumentException iae) {
                            if (iae.getMessage().contains("exists"))
                                i++;
                            if (i >= 99)
                                throw iae;
                        }
                    }
                }
            }
            dstDocument.setAllSecurityToBeRemoved(true);
            dstDocument.save(dstPdf);
        }
    }

    private static PageAngle getPageAndAngleFromFileName(String fileName) {
        // "00001.0.5299606323242188.pdf"
        fileName = FilenameUtils.removeExtension(fileName);
        // "00001.0.5299606323242188"
        String[] nameRotate = fileName.split("\\.");
        PageAngle pa = new PageAngle();
        pa.page = Integer.parseInt(nameRotate[0]);
        if (nameRotate.length > 1) {
            fileName = fileName.substring(nameRotate[0].length() + 1);
            // "0.5299606323242188"
            pa.angle = Double.parseDouble(fileName);
        }
        return pa;
    }

    private static void rotatePageContents(PDDocument origDocument, PDPage dstPage, double contentsRotate) throws IOException {
        PDPageContentStream cs = new PDPageContentStream(
                origDocument,
                dstPage,
                PDPageContentStream.AppendMode.PREPEND,
                false,
                false);
        PDRectangle cropBox = dstPage.getCropBox();
        float tx = (cropBox.getLowerLeftX() + cropBox.getUpperRightX()) / 2;
        float ty = (cropBox.getLowerLeftY() + cropBox.getUpperRightY()) / 2;

        FullAffineMatrix transform = FullAffineMatrix.getTranslateMatrix(tx, ty);
        transform = transform.multiply(FullAffineMatrix.getRotateMatrix(-(float)contentsRotate));
        transform = transform.multiply(FullAffineMatrix.getTranslateMatrix(-tx, -ty));
        Matrix ft = transform.toCvMatrix();
        cs.transform(ft);
        cs.close();
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option pwrd = new Option("p", "password", true,
                "PDF file password.");
        pwrd.setRequired(false);
        options.addOption(pwrd);

        Option originalPDF = new Option("orig", "original-pdf", true,
                "Original PDF file to merge page layers.");
        originalPDF.setRequired(true);
        options.addOption(originalPDF);

        Option pageDir = new Option("pages", "page-dir", true,
                "Directory containing page PDF files named as [page_num_1_based].pdf");
        pageDir.setRequired(false);
        options.addOption(pageDir);

        Option dstPDF = new Option("dst", "dst-pdf", true,
                "File name to save the resulting PDF.");
        dstPDF.setRequired(true);
        options.addOption(dstPDF);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp(MergeInPageLayers.class.getName(), options);
            System.exit(1);
        }
        return null;
    }

}


class FullAffineMatrix {
    public double m[][];

    public FullAffineMatrix() {
        m = new double[][]{{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
    }

    public FullAffineMatrix(double _m[][]) {
        m = _m;
    }

    public Matrix toCvMatrix() {
        return new Matrix((float)m[0][0], (float)m[1][0],
                          (float)m[0][1], (float)m[1][1],
                          (float)m[0][2], (float)m[1][2]);
    }

    public FullAffineMatrix multiply(FullAffineMatrix b) {
        double[][] c = new double[][]{{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
        for(int i=0; i<3; i++) {
            for (int j = 0; j < 3; j++) {
                c[i][j] = 0;
                for (int k = 0; k < 3; k++) {
                    c[i][j] += m[i][k] * b.m[k][j];
                } //end of k loop
            } //end of j loop
        } //end of i loop
        return new FullAffineMatrix(c);
    }

    public static FullAffineMatrix getTranslateMatrix(float tx, float ty) {
        return new FullAffineMatrix(new double[][]{{1, 0, tx}, {0, 1, ty}, {0, 0, 1}});
    }

    public static FullAffineMatrix getScaleMatrix(float sx, float sy) {
        return new FullAffineMatrix(new double[][]{{sx, 0, 0}, {0, sy, 0}, {0, 0, 1}});
    }

    public static FullAffineMatrix getRotateMatrix(float angleDegrees) {
        double a = Math.toRadians(angleDegrees);
        float sin = (float)Math.sin(a);
        float cos = (float)Math.cos(a);
        return new FullAffineMatrix(new double[][]{{cos, sin, 0}, {-sin, cos, 0}, {0, 0, 1}});
    }
}