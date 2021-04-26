package com.lexpredict.textextraction.mergepdf;

import com.lexpredict.textextraction.PDFToTextWithCoordinates;
import com.lexpredict.textextraction.dto.PDFPlainText;
import junit.framework.TestCase;
import org.apache.commons.io.FileUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class TestMergeInPageLayers extends TestCase {

    public void testMergeFromPageDir() throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        Path tempDirPages = Files.createTempDirectory("t");
        try {
            File fOrig = new File(tempDir.toFile(), "ocr_exp1.pdf");
            File fDst = new File(tempDir.toFile(), "ocr_exp1_dst.pdf");
            File fPage2 = new File(tempDirPages.toFile(), "00002.pdf");

            try (InputStream isOrig = TestMergeInPageLayers.class
                    .getResourceAsStream("/ocr_exp1.pdf");
                 InputStream isPage2 = TestMergeInPageLayers.class
                         .getResourceAsStream("/ocr_exp1_page_00002.pdf")) {
                FileUtils.copyToFile(isOrig, fOrig);
                FileUtils.copyToFile(isPage2, fPage2);
            }

            MergeInPageLayers.main(new String[]{
                    "--original-pdf", fOrig.getAbsolutePath(),
                    "--page-dir", tempDirPages.toFile().getAbsolutePath(),
                    "--dst-pdf", fDst.getAbsolutePath()});

            try (PDDocument document = PDDocument.load(fDst, (String) null)) {
                PDFPlainText res = PDFToTextWithCoordinates
                        .process(document, true);
                assertTrue(res.text.contains("Never in history has private"));
            }

        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
            FileUtils.deleteQuietly(tempDirPages.toFile());
        }
    }

    public void testMergeSinglePage() throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        Path tempDirPages = Files.createTempDirectory("t");
        try {
            File fOrig = new File(tempDir.toFile(), "ocr_exp1.pdf");
            File fDst = new File(tempDir.toFile(), "ocr_exp1_dst.pdf");
            File fPage2 = new File(tempDirPages.toFile(), "00002.pdf");

            try (InputStream isOrig = TestMergeInPageLayers.class
                    .getResourceAsStream("/ocr_exp1.pdf");
                 InputStream isPage2 = TestMergeInPageLayers.class
                         .getResourceAsStream("/ocr_exp1_page_00002.pdf")) {
                FileUtils.copyToFile(isOrig, fOrig);
                FileUtils.copyToFile(isPage2, fPage2);
            }

            MergeInPageLayers.main(new String[]{
                    "--original-pdf", fOrig.getAbsolutePath(),
                    "--dst-pdf", fDst.getAbsolutePath(),
                    "1=" + fPage2.getAbsolutePath(),
                    "rotate_1=-5.6789"});

            try (PDDocument document = PDDocument.load(fDst, (String) null)) {
                PDFPlainText res = PDFToTextWithCoordinates
                        .process(document, true);
                assertTrue(res.text.contains("Never in history has private"));
            }

        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
            FileUtils.deleteQuietly(tempDirPages.toFile());
        }
    }


    /*public void testMergePageWithRotation() throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        Path tempDirPages = Files.createTempDirectory("t");
        try {
            File fOrig = new File(tempDir.toFile(), "realdoc__00121_orig.pdf");
            File fDst = new File(tempDir.toFile(), "ocr_exp2_dst.pdf");
            File fPage = new File(tempDirPages.toFile(), "realdoc__00121_ocr_results.pdf");

            try (InputStream isOrig = TestMergeInPageLayers.class
                    .getResourceAsStream("/" + fOrig.getName());
                 InputStream isPage2 = TestMergeInPageLayers.class
                         .getResourceAsStream("/" + fPage.getName())) {
                FileUtils.copyToFile(isOrig, fOrig);
                FileUtils.copyToFile(isPage2, fPage);
            }
            String angle = "-88.49";
            MergeInPageLayers.main(new String[]{
                    "--original-pdf", fOrig.getAbsolutePath(),
                    "--dst-pdf", fDst.getAbsolutePath(),
                    "1=" + fPage.getAbsolutePath(),
                    "rotate_1=" + angle});

            try (PDDocument document = PDDocument.load(fDst, (String) null)) {
                PDFPlainText res = PDFToTextWithCoordinates
                        .process(document, true);
                assertTrue(res.text.contains("Allegan General Hospital"));
            }

        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
            FileUtils.deleteQuietly(tempDirPages.toFile());
        }
    }*/

}
