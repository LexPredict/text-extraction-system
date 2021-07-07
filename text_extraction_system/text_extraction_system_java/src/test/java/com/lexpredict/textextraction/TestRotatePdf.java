package com.lexpredict.textextraction;

import com.lexpredict.textextraction.mergepdf.TestMergeInPageLayers;
import junit.framework.TestCase;
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class TestRotatePdf extends TestCase {
    public void testRotatePage() throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        try {
            File fOrig = new File(tempDir.toFile(), "nine_degree_page.pdf");
            File fDst = new File(tempDir.toFile(), "nine_degree_page_dst.pdf");

            try (InputStream isPage2 = TestMergeInPageLayers.class
                    .getResourceAsStream("/nine_degree_page.pdf")) {
                FileUtils.copyToFile(isPage2, fOrig);
            }

            RotatePdf.main(new String[]{
                    "--original-pdf", fOrig.getAbsolutePath(),
                    "--dst-pdf", fDst.getAbsolutePath(),
                    "--rot-angle", "-9"});

            // check the PDF exists and it's size slightly differs
            TestCase.assertTrue(fDst.isFile());
            long oldLen = fOrig.length();
            long newLen = fDst.length();
            TestCase.assertTrue(newLen > 0.8 * oldLen);
            TestCase.assertTrue(oldLen > 0.8 * newLen);

        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }
}
