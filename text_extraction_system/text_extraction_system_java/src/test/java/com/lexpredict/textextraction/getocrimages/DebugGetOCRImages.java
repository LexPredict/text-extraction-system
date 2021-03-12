package com.lexpredict.textextraction.getocrimages;

import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class DebugGetOCRImages {

    public static void main(String[] args) throws IOException {
        Path tempDir = Files.createTempDirectory("t");
        File f = new File(tempDir.toFile(), "ocr_exp1.pdf");
        try {
            try (InputStream is = DebugGetOCRImages.class.getResourceAsStream("/ocr_exp1.pdf")) {
                FileUtils.copyToFile(is, f);
                GetOCRImages.main(new String[]{f.getAbsolutePath(),
                        "--format", "PNG",
                        "--dpi", "300",
                        "--start-page", "2",
                        "--end-page", "2",
                        "--output-prefix", "/tmp/111/res_"});

            }
        } finally {
            FileUtils.deleteDirectory(tempDir.toFile());
        }
    }

}
