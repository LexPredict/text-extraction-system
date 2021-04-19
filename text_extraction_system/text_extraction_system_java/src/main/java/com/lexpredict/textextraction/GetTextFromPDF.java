package com.lexpredict.textextraction;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexpredict.textextraction.dto.PDFPlainText;
import com.lexpredict.textextraction.dto.PDFPlainTextPage;
import org.apache.commons.cli.*;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.msgpack.jackson.dataformat.MessagePackFactory;

import java.awt.*;
import java.io.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

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
            p.charBBoxes = Arrays.asList(
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
        String debugOutputPDF = cmd.getOptionValue("debug");

        try (PDDocument document = PDDocument.load(new File(pdf), password)) {
            PDFPlainText res = PDFToTextWithCoordinates.process(document);

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

            if (debugOutputPDF != null)
                GetTextFromPDF.renderDebugPDF(document, res, debugOutputPDF);
        }
    }

    protected static void renderDebugPDF(PDDocument document, PDFPlainText res, String fn) throws IOException {
        int i = 0;
        for (PDPage page : document.getPages()) {
            PDFPlainTextPage pageRes = res.pages.get(i);
            List<double[]> pageCoords = res.charBBoxes.subList(pageRes.location[0], pageRes.location[1]);
            String pageText = res.text.substring(pageRes.location[0], pageRes.location[1]);
            List<double[]> lineCoordsStartEnd = new ArrayList<>();
            List<String> lineTexts = new ArrayList<>();
            double[] coordsStart = null;
            int chNumStart = -1;

            for (int chNum = 0; chNum < pageText.length(); chNum++) {
                if (coordsStart == null && pageText.charAt(chNum) != '\n' && pageText.charAt(chNum) != ' ') {
                    double[] charCoords = pageCoords.get(chNum);
                    coordsStart = new double[]{charCoords[0], charCoords[1]};
                    chNumStart = chNum;
                } else if ((pageText.charAt(chNum) == '\n' || pageText.charAt(chNum) == ' ') && chNum > 1 && coordsStart != null) {
                    double[] charCoords = pageCoords.get(chNum - 1);
                    lineCoordsStartEnd.add(new double[]{coordsStart[0], pageRes.bbox[3] - coordsStart[1],
                            charCoords[0] + charCoords[2], pageRes.bbox[3] - charCoords[1]});
                    String sub = pageText.substring(chNumStart, chNum);
                    lineTexts.add(sub);
                    coordsStart = null;
                    chNumStart = -1;
                }
            }
            PDPageContentStream contentStream = new PDPageContentStream(document, page,
                    PDPageContentStream.AppendMode.APPEND, true, true);
            int k = 0;
            for (double[] l : lineCoordsStartEnd) {
                contentStream.setStrokingColor(Color.RED);
                contentStream.moveTo((float) l[0], (float) l[1]);
                contentStream.lineTo((float) l[2], (float) l[3]);
                contentStream.stroke();

                //PDType1Font pdfFont = PDType1Font.HELVETICA;
                //int fontSize = 9;
                //contentStream.setFont(pdfFont, fontSize);
                //contentStream.setStrokingColor(Color.CYAN);
                //contentStream.beginText();
                //contentStream.newLineAtOffset((float) l[0], (float) l[1]);
                //contentStream.showText(lineTexts.get(k));
                //contentStream.endText();
                k++;
            }
            contentStream.close();


            i++;
        }
        document.save(fn);
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option input = new Option("f", "format", true,
                "output format, default = \"plain_text\"");
        input.setRequired(false);
        options.addOption(input);

        Option pwrd = new Option("p", "password", true,
                "PDF file password");
        pwrd.setRequired(false);
        options.addOption(pwrd);

        Option debugOutput = new Option("debug", "debug_pdf_output", true,
                "write debug pdf with the text marked with lines and color");
        debugOutput.setRequired(false);
        options.addOption(debugOutput);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp(GetTextFromPDF.class.getName(), options);
            System.exit(1);
        }
        return null;
    }
}

