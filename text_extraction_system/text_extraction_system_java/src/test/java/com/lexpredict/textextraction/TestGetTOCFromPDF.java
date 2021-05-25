package com.lexpredict.textextraction;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexpredict.textextraction.dto.PDFPlainText;
import com.lexpredict.textextraction.dto.PDFTOCRef;
import junit.framework.TestCase;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.InputStream;
import java.io.StringWriter;
import java.util.List;


public class TestGetTOCFromPDF extends TestCase {
    public void test_get_toc() throws Exception {
        try (InputStream stream = TestPDF2Text.class.getResourceAsStream("/arxiv_06.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                List<PDFTOCRef> refs = GetTOCFromPDF.getTableOfContents(document);
                TestCase.assertTrue(refs.size() > 3);
            }
        }
    }
}