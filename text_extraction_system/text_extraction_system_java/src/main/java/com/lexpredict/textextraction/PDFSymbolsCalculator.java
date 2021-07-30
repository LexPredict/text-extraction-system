package com.lexpredict.textextraction;

import org.apache.commons.cli.*;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.File;
import java.io.IOException;

public class PDFSymbolsCalculator {
    public static void main(String args[]) throws IOException {
        CommandLine cmd = parseCliArgs(args);
        String src = cmd.getOptionValue("original-pdf");

        PDFTextStripper pdfStripper = null;
        try (PDDocument doc = PDDocument.load(new File(src))) {
            pdfStripper = new PDFTextStripper();
            String parsedText = pdfStripper.getText(doc);
            System.out.println(parsedText.length());
        }
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option originalPDF = new Option("orig", "original-pdf", true,
                "Original PDF file to calculate words / symbols.");
        originalPDF.setRequired(true);
        options.addOption(originalPDF);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp(PDFSymbolsCalculator.class.getName(), options);
            System.exit(1);
        }
        return null;
    }
}
