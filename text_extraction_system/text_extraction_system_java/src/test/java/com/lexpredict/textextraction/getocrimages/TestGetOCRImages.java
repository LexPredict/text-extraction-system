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
                    "--output-prefix", tempDir.toString() + "/page_"});
            assertTrue(new File(tempDir.toFile(), "page_00002.png").isFile());
        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }

}
