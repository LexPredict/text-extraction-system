package com.lexpredict.textextraction;

import org.apache.commons.cli.*;

import com.artofsolving.jodconverter.DocumentConverter;
import com.artofsolving.jodconverter.DocumentFamily;
import com.artofsolving.jodconverter.DocumentFormat;
import com.artofsolving.jodconverter.openoffice.connection.OpenOfficeConnection;
import com.artofsolving.jodconverter.openoffice.connection.SocketOpenOfficeConnection;
import com.artofsolving.jodconverter.openoffice.converter.OpenOfficeDocumentConverter;

import java.io.File;
import java.io.IOException;
import java.net.ConnectException;


public class ConvertToPDF {
    public static void main(String[] args) throws IOException, ConnectException {
        CommandLine cmd = parseCliArgs(args);
        String src = cmd.getOptionValue("original-doc");
        String dstPdf = cmd.getOptionValue("dst-pdf");

        File inputFile = new File(src);
        File outputFile = new File(dstPdf);

        // connect to an OpenOffice.org instance running on port 8100
        OpenOfficeConnection connection = new SocketOpenOfficeConnection(8100);
        connection.connect();

        // convert
        DocumentConverter converter = new OpenOfficeDocumentConverter(connection);
        final DocumentFormat docx = new DocumentFormat("Microsoft Word 2007 XML", DocumentFamily.TEXT, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx");
        converter.convert(inputFile, docx, outputFile, null);

        // close the connection
        connection.disconnect();
    }

    protected static CommandLine parseCliArgs(String[] args) {
        Options options = new Options();

        Option originalPDF = new Option("orig", "original-doc", true, "Original document file to convert to PDF.");
        originalPDF.setRequired(true);
        options.addOption(originalPDF);

        Option dstPDF = new Option("dst", "dst-pdf", true, "File name to save the resulting PDF.");
        dstPDF.setRequired(true);
        options.addOption(dstPDF);

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();
        try {
            return parser.parse(options, args);
        } catch (ParseException e) {
            System.out.println(e.getMessage());
            formatter.printHelp(ConvertToPDF.class.getName(), options);
            System.exit(1);
        }
        return null;
    }
}