package com.lexpredict.textextraction;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexpredict.textextraction.dto.PageInfo;
import junit.framework.TestCase;
import org.apache.commons.io.IOUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.List;

public class TestPDF2Text extends TestCase {

    public void test1() throws Exception {
        try (InputStream stream = TestPDF2Text.class.getResourceAsStream("/structured_text.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                List<PageInfo> pages = PDFToTextWithCoordinates.process(document);
                StringBuilder sb = new StringBuilder();
                for (PageInfo p : pages) {
                    sb.append(p.text);
                    sb.append("\n\f");
                }
                System.out.println(sb.toString());
                System.out.println("======================================");
                ObjectMapper om = new ObjectMapper();
                StringWriter sw = new StringWriter();
                om.writerWithDefaultPrettyPrinter().writeValue(sw, pages);
                System.out.println(sw);

                PageInfo p = pages.get(0);
                String txt = p.text.replaceAll("\n", "").replaceAll("\f", "");
                TestCase.assertEquals(txt.length(), p.char_boxes.size());

            }
        }
    }

}
