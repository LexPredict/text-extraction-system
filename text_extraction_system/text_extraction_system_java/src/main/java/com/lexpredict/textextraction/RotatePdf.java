package com.lexpredict.textextraction;

import com.lexpredict.textextraction.mergepdf.MergeInPageLayers;
import org.apache.commons.cli.*;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.util.Matrix;
import java.io.File;
import java.io.IOException;

public class RotatePdf {
    public static void main(String[] args) throws IOException {

        CommandLine cmd = parseCliArgs(args);

        String src = cmd.getOptionValue("original-pdf");
        String dstPdf = cmd.getOptionValue("dst-pdf");
        String angleStr = cmd.getOptionValue("rot-angle");
        double angle = Double.parseDouble(angleStr);

        try (PDDocument dstDocument = PDDocument.load(new File(src))) {
            int count = dstDocument.getNumberOfPages();
            for (int i = 0; i < count; i++) {
                PDPage page = dstDocument.getPage(i);
                rotatePageContents(dstDocument, page, angle);
            }

            dstDocument.setAllSecurityToBeRemoved(true);
            dstDocument.save(dstPdf);
        }
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
        cs.transform(Matrix.getTranslateInstance(tx, ty));
        cs.transform(Matrix.getRotateInstance(Math.toRadians(contentsRotate), 0, 0));
        cs.transform(Matrix.getTranslateInstance(-tx, -ty));
        cs.close();
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option originalPDF = new Option("orig", "original-pdf", true,
                "Original PDF file to merge page layers.");
        originalPDF.setRequired(true);
        options.addOption(originalPDF);

        Option dstPDF = new Option("dst", "dst-pdf", true,
                "File name to save the resulting PDF.");
        dstPDF.setRequired(true);
        options.addOption(dstPDF);

        Option rotAngle = new Option("a", "rot-angle", true,
                "Rotation angle.");
        rotAngle.setRequired(true);
        options.addOption(rotAngle);

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
