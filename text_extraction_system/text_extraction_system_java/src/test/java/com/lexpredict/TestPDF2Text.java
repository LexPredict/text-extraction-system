package com.lexpredict;

import junit.framework.TestCase;
import org.apache.commons.io.IOUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class TestPDF2Text extends TestCase {

    public void test1() throws Exception {
        try (InputStream stream = TestPDF2Text.class.getResourceAsStream("/structured_text.pdf")) {
            Path pText = Files.createTempFile(null, null);
            Path pCoords = Files.createTempFile(null, null);
            Path pPages = Files.createTempFile(null, null);
            PDDocument document = PDDocument.load(stream);

            try (FileOutputStream fwText = new FileOutputStream(pText.toFile())) {
                try (FileOutputStream fwCoords = new FileOutputStream(pCoords.toFile())) {
                    try (FileOutputStream fwPages = new FileOutputStream(pPages.toFile())) {
                        PDF2Text.process(document, fwText, fwCoords, fwPages);
                        printFile(pText.toFile());
                        printFile(pCoords.toFile());
                        printFile(pPages.toFile());
                    }
                }
            }
            document.close();
        }
    }

    protected static void printFile(File file) throws IOException {
        try (FileInputStream frText = new FileInputStream(file)) {
            String body = IOUtils.toString(frText, StandardCharsets.UTF_8.name());
            System.out.println("========================================");
            System.out.println(body);
        }
    }
}
