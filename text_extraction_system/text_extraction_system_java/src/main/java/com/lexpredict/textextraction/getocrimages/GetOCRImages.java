package com.lexpredict.textextraction.getocrimages;

import org.apache.commons.cli.*;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.rendering.ImageType;
import org.apache.pdfbox.rendering.PDFRenderer;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

public class GetOCRImages {

    public static final String ARG_FORMAT = "format";
    public static final String ARG_DPI = "dpi";
    public static final String ARG_PASSWORD = "password";
    public static final String ARG_PREF_NO_TEXT = "output-prefix-no-text";
    public static final String ARG_START_PAGE = "start-page";
    public static final String ARG_END_PAGE = "end-page";
    public static final String ARG_OUTPUT_PREFIX_WITH_TEXT = "output-prefix-with-text";

    public static void main(String[] args) throws IOException {
        String pdf = args[0];
        CommandLine cmd = parseCliArgs(args);

        String format = cmd.getOptionValue(ARG_FORMAT, "PNG");
        float dpi = Float.parseFloat(cmd.getOptionValue(ARG_DPI, "300"));
        String password = cmd.getOptionValue(ARG_PASSWORD, null);
        String outputPrefixNoText = cmd.getOptionValue(ARG_PREF_NO_TEXT, null);
        String outputPrefixWithText = cmd.getOptionValue(ARG_OUTPUT_PREFIX_WITH_TEXT, null);
        String startPageStr = cmd.getOptionValue(ARG_START_PAGE, "1");
        String endPageStr = cmd.getOptionValue(ARG_END_PAGE, null);


        try (PDDocument document = PDDocument.load(new File(pdf), password)) {
            PDFRenderer renderer = new PDFRenderer(document);
            int startPage = Math.max(Integer.parseInt(startPageStr), 1);
            int endPage = endPageStr != null
                    ? Math.min(Integer.parseInt(endPageStr), document.getNumberOfPages())
                    : document.getNumberOfPages();

            for (int i = startPage; i < endPage + 1; i++) {
                PDPage page = document.getPage(i - 1);
                if (outputPrefixWithText != null) {
                    BufferedImage image = renderer.renderImageWithDPI(i - 1, dpi, ImageType.RGB);
                    ImageIO.write(image, format,
                            new File(outputPrefixWithText + String.format("%05d", i) + "." + format.toLowerCase()));

                }

                if (outputPrefixNoText != null) {
                    FindImages fi = new FindImages();
                    fi.processPage(page);
                    PDPageContentStream contentStream = new PDPageContentStream(document, page,
                            PDPageContentStream.AppendMode.OVERWRITE, true);
                    for (FindImages.FoundImage found : fi.found) {
                        contentStream.drawImage(found.imageXObject, found.matrix);
                    }
                    contentStream.close();
                    BufferedImage image = renderer.renderImageWithDPI(i - 1, dpi, ImageType.RGB);
                    ImageIO.write(image, format,
                            new File(outputPrefixNoText + String.format("%05d", i) + "." + format.toLowerCase()));

                }
            }

        }
    }


    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option input = new Option("f", ARG_FORMAT, true,
                "Output image format known to ImageIO. Default: PNG");
        input.setRequired(false);
        options.addOption(input);

        Option output = new Option(ARG_DPI, ARG_DPI, true,
                "Image resolution. Default: 300");
        output.setRequired(false);
        options.addOption(output);

        Option startPage = new Option("start", "start-page", true,
                "Start page (1-based). Default: 1");
        startPage.setRequired(false);
        options.addOption(startPage);

        Option endPage = new Option("end", "end-page", true,
                "End page (1-based). Default: last page of file");
        endPage.setRequired(false);
        options.addOption(endPage);

        Option pwrd = new Option("p", ARG_PASSWORD, true,
                "PDF file password.");
        pwrd.setRequired(false);
        options.addOption(pwrd);

        Option outputPrefixNoText = new Option("output_prefix_no_text",
                ARG_PREF_NO_TEXT,
                true,
                "Prefix including dir/path for the extracted page images with text elements removed.");
        outputPrefixNoText.setRequired(false);
        options.addOption(outputPrefixNoText);

        Option outputPrefixWithText = new Option("output_prefix_with_text",
                ARG_OUTPUT_PREFIX_WITH_TEXT,
                true,
                "Prefix including dir/path for the extracted page images containing both image and text elements.");
        outputPrefixWithText.setRequired(false);
        options.addOption(outputPrefixWithText);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp(GetOCRImages.class.getName(), options);
            System.exit(1);
        }
        return null;
    }
}
