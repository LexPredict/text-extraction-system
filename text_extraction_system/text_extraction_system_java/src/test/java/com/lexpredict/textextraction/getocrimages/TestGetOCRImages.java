package com.lexpredict.textextraction.getocrimages;

import junit.framework.TestCase;
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class TestGetOCRImages extends TestCase {

    public void test1() throws IOException {
        Path tempDir = Files.createTempDirectory("t");
        File f = new File(tempDir.toFile(), "ocr_exp1.pdf");
        try {
            try (InputStream is = TestGetOCRImages.class.getResourceAsStream("/ocr_exp1.pdf")) {
                FileUtils.copyToFile(is, f);
            }
            GetOCRImages.main(new String[]{f.getAbsolutePath(),
                    "--format", "PNG",
                    "--dpi", "300",
                    "--start-page", "2",
                    "--end-page", "2",
                    "--output-prefix-no-text", tempDir.toString() + "/page_no_text_",
                    "--output-prefix-with-text", tempDir.toString() + "/page_with_text_"});
            assertTrue(new File(tempDir.toFile(), "page_no_text_00002.png").isFile());
            assertTrue(new File(tempDir.toFile(), "page_with_text_00002.png").isFile());
        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }

    public void test2ndOcr() throws IOException {
        Path tempDir = Files.createTempDirectory("t");
        File f = new File(tempDir.toFile(), "image_text_overlap.pdf");
        try {
            try (InputStream is = TestGetOCRImages.class.getResourceAsStream("/image_text_overlap.pdf")) {
                FileUtils.copyToFile(is, f);
            }
            GetOCRImages.main(new String[]{f.getAbsolutePath(),
                    "--format", "PNG",
                    "--dpi", "300",
                    "--start-page", "1",
                    "--end-page", "5",
                    "--output-prefix-no-text", tempDir.toString() + "/page_no_text_",
                    "--output-prefix-with-text", tempDir.toString() + "/page_with_text_"});
            assertTrue(new File(tempDir.toFile(), "page_with_text_00001.png").isFile());
            assertFalse(new File(tempDir.toFile(), "page_no_text_00001.png").isFile());

            assertTrue(new File(tempDir.toFile(), "page_with_text_00002.png").isFile());
            assertFalse(new File(tempDir.toFile(), "page_no_text_00002.png").isFile());

            assertTrue(new File(tempDir.toFile(), "page_with_text_00003.png").isFile());
            assertTrue(new File(tempDir.toFile(), "page_no_text_00003.png").isFile());

            assertTrue(new File(tempDir.toFile(), "page_with_text_00004.png").isFile());
            assertTrue(new File(tempDir.toFile(), "page_no_text_00004.png").isFile());

            assertTrue(new File(tempDir.toFile(), "page_with_text_00005.png").isFile());
            assertFalse(new File(tempDir.toFile(), "page_no_text_00005.png").isFile());
        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }


    public void testMistakenlyNotOcred() throws IOException {
        Path tempDir = Files.createTempDirectory("t");
        File f = new File(tempDir.toFile(), "spaces_on_image.pdf");
        try {
            try (InputStream is = TestGetOCRImages.class.getResourceAsStream("/spaces_on_image.pdf")) {
                FileUtils.copyToFile(is, f);
            }
            GetOCRImages.main(new String[]{f.getAbsolutePath(),
                    "--format", "PNG",
                    "--dpi", "300",
                    "--start-page", "1",
                    "--end-page", "1",
                    "--output-prefix-no-text", tempDir.toString() + "/page_no_text_",
                    "--output-prefix-with-text", tempDir.toString() + "/page_with_text_"});
            assertTrue(new File(tempDir.toFile(), "page_with_text_00001.png").isFile());
            assertTrue(new File(tempDir.toFile(), "page_no_text_00001.png").isFile());
        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }

}
