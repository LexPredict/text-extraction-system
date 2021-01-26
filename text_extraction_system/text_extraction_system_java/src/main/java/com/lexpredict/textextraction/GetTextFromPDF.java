package com.lexpredict.textextraction;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexpredict.textextraction.dto.PageInfo;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.msgpack.jackson.dataformat.MessagePackFactory;

import java.io.*;
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
            PageInfo p = new PageInfo();
            p.text = "This is the text of page 1.";
            p.box = new double[]{1d, 2d, 3d, 4d};
            p.char_boxes = Arrays.asList(new double[]{5d, 6d, 7d, 8d}, new double[]{9d, 10d, 11d, 12d});

            PageInfo p1 = new PageInfo();
            p1.text = "Bounding box of each page is in 'box' field in format [x, y, width, height]";
            p1.box = new double[]{1d, 2d, 3d, 4d};
            p1.char_boxes = Arrays.asList(new double[]{5d, 6d, 7d, 8d}, new double[]{9d, 10d, 11d, 12d});

            PageInfo p2 = new PageInfo();
            p2.text = "PDF coordinates of each character of the text on the page are in 'char_boxes' field in\n" +
                    "the same format: [[x, y, width, height], [x, y, width, height] ... [x, y, width, height]] ";
            p2.box = new double[]{1d, 2d, 3d, 4d};
            p2.char_boxes = Arrays.asList(new double[]{5d, 6d, 7d, 8d}, new double[]{9d, 10d, 11d, 12d});


            String example = om.writerWithDefaultPrettyPrinter().writeValueAsString(Arrays.asList(p, p1, p2));
            System.out.println("JSON / MsgPack output example:\n" + example);
            System.out.println(Arrays.asList(args));

            return;
        }

        String pdf = args[0];
        String outFn = args[1];
        String format = PLAIN_TEXT;
        if (args.length > 2) format = args[2];

        String password = null;
        if (args.length > 3) password = args[3];

        try (PDDocument document = PDDocument.load(new File(pdf), password)) {
            List<PageInfo> pages = PDFToTextWithCoordinates.process(document);

            try (OutputStream os = new FileOutputStream(outFn)) {
                if (PLAIN_TEXT.equals(format)) {
                    StringBuilder sb = new StringBuilder();
                    for (PageInfo p : pages) {
                        sb.append(p.text);
                        sb.append("\f");
                    }
                    try (Writer w = new OutputStreamWriter(os)) {
                        w.write(sb.toString());
                    }
                } else if (PAGES_JSON.equals(format)) {
                    ObjectMapper om = new ObjectMapper();
                    om.writerWithDefaultPrettyPrinter().writeValue(os, pages);
                } else if (PAGES_MSGPACK.equals(format)) {
                    ObjectMapper om = new ObjectMapper(new MessagePackFactory());
                    om.writeValue(os, pages);
                }
            }
        }
    }

}

