package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PDFPlainText;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.File;
import java.io.InputStream;

public class DebugTextExtraction {

    public static void test_vertical_doc_deskew_90() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/vertical_90.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void test_vertical_doc_deskew_270() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/vertical_270.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void test_vertical_doc_deskew_x_90() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/vertical_x_90.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void test_hor_x_0() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/hor_x_0.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void test_hor_x_small_angles() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/hor_x_small_angles.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void test_hor_x_small_angles_many() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/hor_x_small_angles_many.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void test_hor_x_small_angles_many_a5() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/hor_x_small_angles_many_a5.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }



    public static void test_wrong_angle6() throws Exception {
        try (InputStream stream = TestPDF2Text.class
                .getResourceAsStream("/wrong_angle6.ocred.pdf")) {
            try (PDDocument document = PDDocument.load(stream)) {
                PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
                document.save("/tmp/000.pdf");
                GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
            }
        }
    }

    public static void main(String[] args) throws Exception {
        //DebugTextExtraction.test_wrong_angle6();
        try (PDDocument document = PDDocument.load(new File("/home/mikhail/lexpredict/misc/angles/album_90_orig.pdf"))) {
            document.getPage(0).setRotation(90);
            document.save("/home/mikhail/lexpredict/misc/angles/album_90.pdf");
        }
    }
}
