package com.lexpredict.textextraction.mergepdf;

import org.apache.commons.cli.*;
import org.apache.pdfbox.multipdf.LayerUtility;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.graphics.form.PDFormXObject;

import java.awt.geom.AffineTransform;
import java.io.File;
import java.io.FileFilter;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class MergeInPageLayers {

    private static final String EXT_PDF = ".pdf";

    public static void main(String[] args) throws IOException {

        CommandLine cmd = parseCliArgs(args);

        String pdf = cmd.getOptionValue("original-pdf");
        String pagesDirStr = cmd.getOptionValue("page-dir");
        String password = cmd.getOptionValue("password");
        String dstPdf = cmd.getOptionValue("dst-pdf");

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

        Map<Integer, File> pageToFn = new HashMap<>();
        for (File fn : pageFiles) {
            String[] nameExt = fn.getName().split("\\.");
            try {
                int page = Integer.parseInt(nameExt[0]);
                pageToFn.put(page, fn);
            } catch (NumberFormatException nfe) {
                //continue
            }
        }

        if (pageToFn.isEmpty()) {
            System.out.println("Page directory does not contain page files named [int_page_num].pdf\n" + pagesDirStr);
        }

        try (PDDocument origDocument = PDDocument.load(new File(pdf), password)) {
            LayerUtility layerUtility = new LayerUtility(origDocument);
            for (Map.Entry<Integer, File> pageFn : pageToFn.entrySet()) {
                int pageNumZeroBased = pageFn.getKey() - 1;
                try (PDDocument mergePageDocument = PDDocument.load(pageFn.getValue(), (String) null)) {
                    PDFormXObject textPageForm = layerUtility.importPageAsForm(mergePageDocument, 0);
                    PDPage dstPage = origDocument.getPage(pageNumZeroBased);
                    layerUtility.wrapInSaveRestore(dstPage);

                    PDRectangle destBox = dstPage.getBBox();
                    PDRectangle sourceBox = textPageForm.getBBox();
                    double scaleX = destBox.getWidth()/sourceBox.getWidth();
                    double scaleY = destBox.getHeight()/sourceBox.getHeight();
                    AffineTransform affineTransform = new AffineTransform();
                    affineTransform.scale(scaleX, scaleY);
                    //.getTranslateInstance(0, destCrop.getUpperRightY() - sourceBox.getHeight());
                    layerUtility.appendFormAsLayer(dstPage, textPageForm, affineTransform, "OCRed Text");
                }
            }
            origDocument.save(dstPdf);
        }
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
        pageDir.setRequired(true);
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
