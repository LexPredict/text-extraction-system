package com.lexpredict;

import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageTree;
import org.apache.pdfbox.pdmodel.PDResources;
import org.apache.pdfbox.pdmodel.graphics.PDXObject;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;
import org.apache.pdfbox.tools.PDFToImage

import javax.imageio.ImageIO;
import java.io.File;
import java.io.IOException;

public class ExtractPageImages {

    public static void main(String[] args) {
        if (args.length < 5) {
            System.out.println("Render pages from a PDF file to images.");
            System.out.println("Usage: java -classpath .... "
                    + ExtractPageImages.class.getName()
                    + " <input.pdf> <format:png|jpeg|imageio_known_format> <dst_dir_for_images> <image_name_prefix>");
        }

        String inputPdf = args[1];
        String format = args[2];
        String dstDir = args[3];
        String prefix = args[4];


        try (final PDDocument document = PDDocument.load(new File(inputPdf))) {
            PDPageTree list = document.getPages();
            for (PDPage page : list) {
                PDResources pdResources = page.getResources();
                int i = 1;
                for (COSName name : pdResources.getXObjectNames()) {
                    PDXObject o = pdResources.getXObject(name);
                    if (o instanceof PDImageXObject) {
                        PDImageXObject image = (PDImageXObject) o;
                        String filename = prefix + i + "." + format;
                        ImageIO.write(image.getImage(), format, new File(filename));
                        i++;
                    }
                }
            }

        } catch (IOException e) {
            System.err.println("Exception while trying to create pdf document - " + e);
        }
    }
}
