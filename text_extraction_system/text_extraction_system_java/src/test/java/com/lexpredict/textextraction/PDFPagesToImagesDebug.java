package com.lexpredict.textextraction;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.interactive.form.PDAcroForm;
import org.apache.pdfbox.rendering.ImageType;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.pdfbox.tools.imageio.ImageIOUtil;

import javax.imageio.ImageIO;
import javax.imageio.ImageWriter;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

public class PDFPagesToImagesDebug {

    public static void main(String[] args) throws IOException {
        String fn = args[0];
        String outputFormat = args[1];
        String outputPrefix = args[2];
        String password = null;
        boolean subsampling = false;
        int dpi = 300;

        int startPage = 0;
        int endPage = Integer.MAX_VALUE;
        if (args.length > 3) {
            startPage = Integer.parseInt(args[3]);
        }

        if (args.length > 4) {
            endPage = Integer.parseInt(args[4]);
        }

        String writerClass = null;
        if (outputFormat.contains(":")) {
            String[] ar = outputFormat.split(":");
            outputFormat = ar[0];
            writerClass = ar[1];
        }

        try (PDDocument document = PDDocument.load(new File(fn), password);) {
            PDAcroForm acroForm = document.getDocumentCatalog().getAcroForm();
            if (acroForm != null && acroForm.getNeedAppearances())
                acroForm.refreshAppearances();

            // render the pages
            boolean success = true;
            endPage = Math.min(endPage, document.getNumberOfPages());
            PDFRenderer renderer = new PDFRenderer(document);
            renderer.setSubsamplingAllowed(subsampling);
            for (int i = startPage - 1; i < endPage; i++) {
                BufferedImage image = renderer.renderImageWithDPI(i, 72f, ImageType.BINARY);


                /*JFrame frame = new JFrame();
                frame.getContentPane().setLayout(new FlowLayout());
                frame.getContentPane().add(new JLabel(new ImageIcon(image)));
                frame.pack();
                frame.setVisible(true);
*/

                String fileName = outputPrefix + (i + 1) + "." + outputFormat;
                success &= ImageIOUtil.writeImage(image, fileName, dpi, 1);
            }

            if (!success) {
                System.err.println("Error: no writer found for image format '"
                        + outputFormat + "'");
                System.exit(1);
            }
        }

    }

    private static ImageWriter getImageWriter(String outputFormat, String writerClass) {
        Iterator<ImageWriter> writers = ImageIO.getImageWritersByFormatName(outputFormat);

        if (!writers.hasNext()) {
            throw new IllegalArgumentException("No writer for: " + outputFormat);
        }


        ImageWriter writer = null;

        if (writerClass == null) {
            return writers.next();
        } else {
            List<String> supportedClasses = new ArrayList<>();
            while (writers.hasNext()) {
                ImageWriter tw = writers.next();
                supportedClasses.add(tw.getClass().getName());
                if (tw.getClass().getName().equals(writerClass)) {
                    return tw;
                }
            }
            throw new IllegalArgumentException(MessageFormat.format(
                    "There is no registered ImageWriter " +
                            "for format {0} with class name {1}\n" +
                            "Supported writer classes are:\n{2}",
                    outputFormat, writerClass, supportedClasses));
        }
    }
}
