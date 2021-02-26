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
                PDFPlainText res = PDFToTextWithCoordinates.process(document, false, false);
                System.out.println(res.text);
                System.out.println("======================================");
                ObjectMapper om = new ObjectMapper();
                StringWriter sw = new StringWriter();
                om.writerWithDefaultPrettyPrinter().writeValue(sw, res);
                System.out.println(sw);

                TestCase.assertEquals(res.text.length(), res.charBBoxesWithPageNums.size());

                int numPages = StringUtils.countMatches(res.text, '\f');
                TestCase.assertEquals(2, numPages);

            }
        }
    }


    public void test_paragraphs() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/RESO_20120828-01_Building_Remodel__1.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, false, false);
                System.out.println(res.text);

                assertEquals("Test document contains 7 paragraphs starting with 'WHEREAS'.",
                        StringUtils.countMatches(res.text, "\n\nWHEREAS"), 7);

                assertTrue("It should not add obsolete empty line after each line of text " +
                                "(paragraph false-positives). Tuned by PDFTextStripper.setDropThreshold().",
                        res.text.contains("with \nthe powers"));
            }
        }
    }

    public void test_paragraphs1() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/RESO_20120828-01_Building_Remodel__54.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, false, false);
                System.out.println(res.text);

            }
        }
    }

}
