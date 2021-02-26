package com.lexpredict.textextraction;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexpredict.textextraction.dto.PDFPlainText;
import com.lexpredict.textextraction.dto.PDFPlainTextPage;
import org.apache.commons.cli.*;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.msgpack.jackson.dataformat.MessagePackFactory;

import java.io.*;
import java.util.Arrays;

public class GetTextFromPDF {

    public static final String PAGES_JSON = "pages_json";
    public static final String PLAIN_TEXT = "plain_text";
    public static final String PAGES_MSGPACK = "pages_msgpack";

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.out.println("Extract text from text-based PDF (no OCR).");
            System.out.println("Usage: java -classpath .... "
                    + GetTextFromPDF.class.getName()
                    + " <pdf_fn> <output_fn> [" + PLAIN_TEXT + "|" + PAGES_JSON + "|" + PAGES_MSGPACK + "] [password]");
            ObjectMapper om = new ObjectMapper();
            PDFPlainText p = new PDFPlainText();
            p.text = "This is the extracted plain text of the document.\n" +
                    "It contains line breaks and FF chars (\f) for page breaks.\n" +
                    "Page bounding boxes are represented by 4-coordinate arrays of double: \n" +
                    "[x, y, width, height].\n " +
                    "Page locations in plain text are represented by 2-coordinate arrays of int: \n" +
                    "[offset_of_first_char_on_page_in_text, offset_of_last_char_on_page_in_text + 1].\n" +
                    "Most likely only width and height of pages make sense in bboxes but " +
                    "in PDFBox they are bboxes so we leave 4 coordinates too.\n" +
                    "Character bboxes are represented by a list of 5-coordinate array of double: \n" +
                    "[page_num, x_on_page, y_on_page, width, height].\n" +
                    "Line-breaks, form feed and other separators are represented by nulls in the list.\n\n" +
                    "Everything is packed in arrays instead of proper json structure to decrease the size of the " +
                    "final output (especially for character coordinates).";
            p.charBBoxesWithPageNums = Arrays.asList(
                    new double[]{1d, 5.6d, 6.7d, 7.8d, 8.9d},
                    new double[]{1d, 5.6d, 6.7d, 7.8d, 8.9d},
                    null,
                    new double[]{1d, 5.6d, 6.7d, 7.8d, 8.9d},
                    null,
                    new double[]{2d, 5.6d, 6.7d, 7.8d, 8.9d},
                    new double[]{2d, 5.6d, 6.7d, 7.8d, 8.9d});


            p.pages = Arrays.asList(new PDFPlainTextPage(new double[]{0, 0, 4.5, 5.6}, new int[]{1, 100}),
                    new PDFPlainTextPage(new double[]{0, 0, 4.5, 5.6}, new int[]{100, 200}));

            String example = om.writerWithDefaultPrettyPrinter().writeValueAsString(p);
            System.out.println("JSON / MsgPack output example:\n" + example);
            System.out.println(Arrays.asList(args));

            return;
        }

        String pdf = args[0];
        String outFn = args[1];
        CommandLine cmd = parseCliArgs(args);

        String format = cmd.getOptionValue("f", PLAIN_TEXT);
        String password = cmd.getOptionValue("p", "");
        String glyphEnhancing = cmd.getOptionValue("ge", "false");
        boolean glyphEnch = glyphEnhancing.equalsIgnoreCase("true");
        String remNonPrintStr = cmd.getOptionValue("rn", "false");
        boolean remNonPrint = remNonPrintStr.equalsIgnoreCase("true");

        try (PDDocument document = PDDocument.load(new File(pdf), password)) {
            PDFPlainText res = PDFToTextWithCoordinates.process(document, glyphEnch, remNonPrint);
            try (OutputStream os = new FileOutputStream(outFn)) {
                if (PLAIN_TEXT.equals(format)) {
                    try (Writer w = new OutputStreamWriter(os)) {
                        w.write(res.text);
                    }
                } else if (PAGES_JSON.equals(format)) {
                    ObjectMapper om = new ObjectMapper();
                    om.writerWithDefaultPrettyPrinter().writeValue(os, res);
                } else if (PAGES_MSGPACK.equals(format)) {
                    ObjectMapper om = new ObjectMapper(new MessagePackFactory());
                    om.writeValue(os, res);
                }
            }
        }
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option input = new Option("f", "format", true,
                "output format, default = \"plain_text\"");
        input.setRequired(false);
        options.addOption(input);

        Option output = new Option("ge", "glyph_enhancing", true,
                "glyph box detection enhancing on (true) / off (false)");
        output.setRequired(false);
        options.addOption(output);

        Option nonPrint = new Option("rn", "remove_non_printable", true,
                "remove non printable symbols");
        nonPrint.setRequired(false);
        options.addOption(nonPrint);

        Option pwrd = new Option("p", "password", true,
                "PDF file password");
        pwrd.setRequired(false);
        options.addOption(pwrd);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp("utility-name", options);
            System.exit(1);
        }
        return null;
    }
}

