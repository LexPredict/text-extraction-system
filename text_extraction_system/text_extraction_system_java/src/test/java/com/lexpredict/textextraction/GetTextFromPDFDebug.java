package com.lexpredict.textextraction;

import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class GetTextFromPDFDebug {

    public static void main(String[] args) throws Exception {
        Path tempDir = Files.createTempDirectory("t");
        File f = new File(tempDir.toFile(), "structured_text.pdf");
        try {
            try (InputStream is = GetTextFromPDFDebug.class.getResourceAsStream("/structured_text.pdf")) {
                FileUtils.copyToFile(is, f);
                GetTextFromPDF.main(new String[] {f.getAbsolutePath(), "pages_msgpack"});
            }
        } finally {
            FileUtils.deleteDirectory(tempDir.toFile());
        }

    }
}
