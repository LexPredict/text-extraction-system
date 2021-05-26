package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PDFTOCRef;
import junit.framework.TestCase;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.InputStream;
import java.util.List;


public class TestGetTOCFromPDF extends TestCase {
    public void test_doc_with_named_destinations() throws Exception {
        try (InputStream stream = TestPDF2Text.class.getResourceAsStream("/arxiv_06.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                List<PDFTOCRef> refs = GetTOCFromPDF.getTableOfContents(document);
                TestCase.assertTrue(refs.size() > 6);
            }
        }
    }

    public void test_doc_with_direct_destinations() throws Exception {
        try (InputStream stream = TestPDF2Text.class.getResourceAsStream("/re_ocr.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                List<PDFTOCRef> refs = GetTOCFromPDF.getTableOfContents(document);
                TestCase.assertTrue(refs.size() > 8);
            }
        }
    }
}