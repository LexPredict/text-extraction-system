package com.lexpredict.textextraction;

import junit.framework.TestCase;
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class TestMakePDFFromImages extends TestCase {

    public void test1() throws IOException {
        this.tryMakingPDFFromImage("/tiff_test.tiff");
    }

    public void test2() throws IOException {
        this.tryMakingPDFFromImage("/transparent.png");
    }

    private void tryMakingPDFFromImage(String image_res) throws IOException {
        Path tempDir = Files.createTempDirectory(null);
        try {
            Path inputImage = tempDir.resolve(new File(image_res).getName());
            Path outputPdf = tempDir.resolve("output.pdf");

            try (InputStream is = this.getClass().getResourceAsStream(image_res)) {
                Files.copy(is, inputImage);
            }
            MakePDFFromImages.main(new String[]{outputPdf.normalize().toString(), inputImage.normalize().toString()});

            TestCase.assertTrue(outputPdf.toFile().isFile());
        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }

    }

}
