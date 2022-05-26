package com.lexpredict.textextraction;

import com.lexpredict.textextraction.mergepdf.MergeInPageLayers;
import com.lexpredict.textextraction.errors.InjuredDocumentException;

import org.apache.commons.cli.*;
import org.apache.pdfbox.cos.COSDictionary;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;


public class RemovePdfText {
    /*
    RemovePdfText class receives 2 arguments:
     -orig: original (source) PDF file path
     -dst: destination PDF file path
     The class creates a copy of the original document WITHOUT all OCR-generated
     text layers.
    * Usage example:
    * RemovePdfText.main(new String[] { "-orig", "/home/andrey/Downloads/DTIC_preproc_02.pdf",
                                                 "-dst", "/home/andrey/Downloads/non_text.pdf"});
    */

    public static class COGMatcher implements MarkedContentRemover.MarkedContentMatcher {

        @Override
        public boolean matches(COSName contentId, COSDictionary props) {
            return contentId.getName().equals("OliveGeneratedContent");
        }
    }

    public static void main(String[] args) throws IOException, InjuredDocumentException {
        CommandLine cmd = parseCliArgs(args);
        String src = cmd.getOptionValue("original-pdf");
        String dstPdf = cmd.getOptionValue("dst-pdf");
        boolean rmText = Arrays.stream(cmd.getOptions())
                .anyMatch(x -> (x.getOpt() == null ? "" : x.getOpt()).equals("rmtext"));

        PDDocument newDoc = new PDDocument();
        MarkedContentRemover rm = new MarkedContentRemover(new COGMatcher());

        try (PDDocument dstDocument = PDDocument.load(new File(src))) {
            int count = dstDocument.getNumberOfPages();
            for (int i = 0; i < count; i++) {
                PDPage page = dstDocument.getPage(i);
                COSDictionary pageDict = page.getCOSObject();
                COSDictionary newPageDict = new COSDictionary(pageDict);

                PDPage newPage = new PDPage(newPageDict);
                newDoc.addPage(newPage);
                if (rmText)
                    rm.removeAllTextContent(newDoc, newPage);
                else
                    rm.removeMarkedContent(newDoc, newPage);
            }

            newDoc.setAllSecurityToBeRemoved(true);
            newDoc.save(dstPdf);
        } catch (IOException e) {
            throw new InjuredDocumentException();
        }
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option originalPDF = new Option("orig", "original-pdf", true,
                "Original PDF file to drop page layers.");
        originalPDF.setRequired(true);
        options.addOption(originalPDF);

        Option dstPDF = new Option("dst", "dst-pdf", true,
                "File name to save the resulting PDF.");
        dstPDF.setRequired(true);
        options.addOption(dstPDF);

        Option removeTextOps = new Option("rmtext", "rm-text", false,
                "Remove all text operators.");
        removeTextOps.setRequired(false);
        options.addOption(removeTextOps);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp(MergeInPageLayers.class.getName(), options);
            System.exit(1);
        }
        return null;
    }
}
