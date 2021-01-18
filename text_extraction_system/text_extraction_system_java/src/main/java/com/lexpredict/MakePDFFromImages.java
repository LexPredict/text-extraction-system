package com.lexpredict;

import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.graphics.PDXObject;
import org.apache.pdfbox.pdmodel.graphics.image.LosslessFactory;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;

public class MakePDFFromImages {

    public static void main(String[] args) throws IOException {
        if (args.length < 3) {
            System.out.println("Make PDF from a set of page images.");
            System.out.println("Usage: java -classpath .... "
                    + MakePDFFromImages.class.getName()
                    + " <dst_pdf_fn> <image_fn_1> <image_fn_2> ... <image_fn_n>");
        }

        String outPdf = args[1];



        PDDocument document=new PDDocument();

        for (int arg = 2; arg < args.length; arg++) {
            String inputImageFn = args[arg];
            File file = new File(inputImageFn);

            try (ImageInputStream isb = ImageIO.createImageInputStream(file)) {

                Iterator<ImageReader> iterator = ImageIO.getImageReaders(isb);
                if (iterator == null || !iterator.hasNext()) {
                    throw new IOException("Image file format not supported by ImageIO: " + inputImageFn);
                }
                ImageReader reader = iterator.next();

                reader.setInput(isb);

                int nbPages = reader.getNumImages(true);
                for (int p = 0; p < nbPages; p++) {
                    BufferedImage bufferedImage = reader.read(p);

                    PDPage page = new PDPage();
                    document.addPage(page);

                    PDImageXObject i = LosslessFactory.createFromImage(document, bufferedImage);

                    PDPageContentStream content = new PDPageContentStream(document, page);
                    content.drawImage(i, 0, 0, page.getMediaBox().getWidth(), page.getMediaBox().getHeight());

                    content.close();
                }
            }
        }
        document.save(outPdf);
        document.close();
    }
}
