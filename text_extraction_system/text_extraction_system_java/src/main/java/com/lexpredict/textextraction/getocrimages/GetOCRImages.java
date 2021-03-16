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

    public static void main(String[] args) throws IOException {
        String pdf = args[0];
        CommandLine cmd = parseCliArgs(args);

        String format = cmd.getOptionValue("format", "PNG");
        float dpi = Float.parseFloat(cmd.getOptionValue("dpi", "300"));
        String password = cmd.getOptionValue("password", null);
        String outputPrefix = cmd.getOptionValue("output-prefix", null);
        String startPageStr = cmd.getOptionValue("start-page", "1");
        String endPageStr = cmd.getOptionValue("end-page", null);


        try (PDDocument document = PDDocument.load(new File(pdf), password)) {
            for (PDPage page : document.getPages()) {
                FindImages fi = new FindImages();
                fi.processPage(page);
                PDPageContentStream contentStream = new PDPageContentStream(document, page,
                        PDPageContentStream.AppendMode.OVERWRITE, true);
                for (FindImages.FoundImage found : fi.found) {
                    contentStream.drawImage(found.imageXObject, found.matrix);
                }
                contentStream.close();
            }

            PDFRenderer renderer = new PDFRenderer(document);
            int startPage = Math.max(Integer.parseInt(startPageStr), 1);
            int endPage = endPageStr != null
                    ? Math.min(Integer.parseInt(endPageStr), document.getNumberOfPages())
                    : document.getNumberOfPages();
            for (int i = startPage; i < endPage + 1; i++) {
                BufferedImage image = renderer.renderImageWithDPI(i - 1, dpi, ImageType.RGB);
                ImageIO.write(image, format,
                        new File(outputPrefix + String.format("%05d", i) + "." + format.toLowerCase()));

            }

        }
    }


    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option input = new Option("f", "format", true,
                "Output image format known to ImageIO. Default: PNG");
        input.setRequired(false);
        options.addOption(input);

        Option output = new Option("dpi", "dpi", true,
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

        Option pwrd = new Option("p", "password", true,
                "PDF file password.");
        pwrd.setRequired(false);
        options.addOption(pwrd);

        Option outputPrefix = new Option("op", "output-prefix", true,
                "Output image file name prefix.");
        outputPrefix.setRequired(true);
        options.addOption(outputPrefix);

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
