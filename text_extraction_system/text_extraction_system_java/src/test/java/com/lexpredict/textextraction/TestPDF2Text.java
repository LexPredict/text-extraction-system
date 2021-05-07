package com.lexpredict.textextraction;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexpredict.textextraction.dto.PDFPlainText;
import junit.framework.TestCase;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.InputStream;
import java.io.StringWriter;


public class TestPDF2Text extends TestCase {

    public void test1() throws Exception {
        try (InputStream stream = TestPDF2Text.class.getResourceAsStream("/structured_text.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                System.out.println(res.text);
                System.out.println("======================================");
                ObjectMapper om = new ObjectMapper();
                StringWriter sw = new StringWriter();
                om.writerWithDefaultPrettyPrinter().writeValue(sw, res);
                System.out.println(sw);

                TestCase.assertEquals(res.text.length(), res.charBBoxes.size());

                int numPages = StringUtils.countMatches(res.text, '\f');
                TestCase.assertEquals(2, numPages);

            }
        }
    }





    public void test_duplication_in_rotated_text2() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/vertical_page_rotated.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                assertEquals(1, StringUtils.countMatches(res.text,
                        "beneficiaries are also paid at prospectively determined rates per discharge"));
            }
        }
    }


    public void test_duplication_in_rotated_text3() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/two_angles.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                assertEquals(2, StringUtils.countMatches(res.text, "Hello hello"));
                assertEquals(1, StringUtils.countMatches(res.text, "Again"));
                assertEquals(3, StringUtils.countMatches(res.text, "again"));
                assertEquals(1, StringUtils.countMatches(res.text, "World"));
                assertEquals(3, StringUtils.countMatches(res.text, "world"));
            }
        }
    }

    public void test_angle() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/rotated1_pdf.converted.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                System.out.println(res.text);

                String t = "certain angle 1";

                assertTrue(res.text.contains(t));
            }
        }
    }

}
