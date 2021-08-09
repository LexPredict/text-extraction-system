package com.lexpredict.textextraction;

import junit.framework.TestCase;
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class TestCalculateSymbols extends TestCase {
    public void testRotatePage() throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        try {
            File fOrig = new File(tempDir.toFile(), "wrd_src.pdf");
            try (InputStream isPage2 = TestRotatePdf.class
                    .getResourceAsStream("/wrd_src.pdf")) {
                FileUtils.copyToFile(isPage2, fOrig);
            }
            PDFSymbolsCalculator.main(new String[] {"--original-pdf", fOrig.getAbsolutePath()});
        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }
}
