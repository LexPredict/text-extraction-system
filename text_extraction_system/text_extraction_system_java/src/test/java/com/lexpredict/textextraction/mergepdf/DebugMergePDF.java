package com.lexpredict.textextraction.mergepdf;

import org.apache.commons.io.FileUtils;
import org.apache.pdfbox.examples.util.DrawPrintTextLocations;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class DebugMergePDF {

    public static void main(String[] args) throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        try {
            File fMergeTo = new File(tempDir.toFile(), "merge_to.pdf");
            File fText = new File(tempDir.toFile(), "text.pdf");
            File fOut = new File(tempDir.toFile(), "output.pdf");
            File fOutDebug = new File(tempDir.toFile(), "output_debug.pdf");

            try (InputStream isMergeTo = DebugMergePDF.class
                    .getResourceAsStream("/finstat90_rotation_set.pdf");
                 InputStream isText = DebugMergePDF.class
                         .getResourceAsStream("/finstat90_rotation_set__text.pdf")) {
                FileUtils.copyToFile(isMergeTo, fMergeTo);
                FileUtils.copyToFile(isText, fText);
            }

            MergeInPageLayers.main(new String[]{
                    "--original-pdf", fMergeTo.getAbsolutePath(),
                    "1=" + fText.getAbsolutePath(),
                    "--dst-pdf", fOut.getAbsolutePath()});

            DrawPrintTextLocations.main(new String[]{fOut.getAbsolutePath()});

        } finally {
            FileUtils.deleteQuietly(tempDir.toFile());
        }
    }
}
