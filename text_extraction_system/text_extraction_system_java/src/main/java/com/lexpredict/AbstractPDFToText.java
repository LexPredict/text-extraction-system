/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Modifications copyright (C) 2020 ContraxSuite, LLC
 */

package com.lexpredict;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageTree;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDFont;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDDocumentOutline;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineItem;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineNode;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.util.Matrix;
import org.apache.pdfbox.util.Vector;
import org.xml.sax.SAXException;
import org.xml.sax.helpers.AttributesImpl;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.NumberFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

class AbstractPDF2Text extends PDFTextStripper {
    /**
     * Maximum recursive depth during AcroForm processing.
     * Prevents theoretical AcroForm recursion bomb.
     */
    private final static int MAX_ACROFORM_RECURSIONS = 10;

    /**
     * Format used for signature dates
     * TODO Make this thread-safe
     */
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.ROOT);
    protected NumberFormat defaultNumberFormat = NumberFormat.getInstance(new Locale("en", "US"));

    final List<IOException> exceptions = new ArrayList<>();
    final PDDocument pdDocument;
    int pageIndex = 0;
    int startPage = -1;
    int unmappedUnicodeCharsPerPage = 0;
    int totalCharsPerPage = 0;
    protected final OutputStream fwText, fwCoords, fwPages;

    AbstractPDF2Text(PDDocument pdDocument,
                     OutputStream fwText,
                     OutputStream fwCoords,
                     OutputStream fwPages) throws IOException {
        this.pdDocument = pdDocument;
        this.fwText = fwText;
        this.fwCoords = fwCoords;
        this.fwPages = fwPages;
    }

    @Override
    protected void startPage(PDPage page) throws IOException {
        StringBuilder sb = new StringBuilder();
        PDRectangle area = page.getMediaBox();
        sb.append(area.getLowerLeftX());
        sb.append(",");
        sb.append(area.getLowerLeftY());
        sb.append(",");
        sb.append(area.getWidth());
        sb.append(",");
        sb.append(area.getHeight());
        sb.append(",");
        sb.append(startPage);

        writeToBuffer(sb, fwPages, true);
    }

    protected void writeToBuffer(StringBuilder s, OutputStream fs, Boolean newLine) throws IOException {
        writeToBuffer(s.toString(), fs, newLine);
    }

    protected void writeToBuffer(String s, OutputStream fs, Boolean newLine) throws IOException {
        if (newLine)
            fs.write((s + "\n").getBytes(StandardCharsets.UTF_8));
        else
            fs.write(s.getBytes(StandardCharsets.UTF_8));
    }

    protected String formatFloatNumbers(String termination, float ...n)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n.length; i++) {
            sb.append(defaultNumberFormat.format(n[i]));
            if (i < n.length - 1)
                sb.append(",");
        }
        sb.append(termination);
        return sb.toString();
    }

    @Override
    protected void endPage(PDPage page) throws IOException {
        totalCharsPerPage = 0;
        unmappedUnicodeCharsPerPage = 0;
    }

    @Override
    protected void startDocument(PDDocument pdf) {
    }

    private static void addNonNullAttribute(String name, String value, AttributesImpl attributes) {
        if (name == null || value == null) {
            return;
        }
        attributes.addAttribute("", name, name, "CDATA", value);
    }

    @Override
    protected void endDocument(PDDocument pdf) throws IOException {
        try {
            // Extract text for any bookmarks:
            extractBookmarkText();
        } catch (Exception e) {
            throw new IOException("Unable to end a document", e);
        }
    }

    void extractBookmarkText() throws SAXException, IOException {
        PDDocumentOutline outline = document.getDocumentCatalog().getDocumentOutline();
        if (outline != null) {
            extractBookmarkText(outline);
        }
    }

    void extractBookmarkText(PDOutlineNode bookmark){
        /*PDOutlineItem current = bookmark.getFirstChild();

        if (current != null) {
            xhtml.startElement("ul");
            while (current != null) {
                xhtml.startElement("li");
                xhtml.characters(current.getTitle());
                xhtml.endElement("li");
                handleDestinationOrAction(current.getAction(), AbstractPDF2XHTML.ActionTrigger.BOOKMARK);
                // Recurse:
                extractBookmarkText(current);
                current = current.getNextSibling();
            }
            xhtml.endElement("ul");
        }*/
    }
    /**
     * we need to override this because we are overriding {@link #processPages(PDPageTree)}
     * @return
     */
    @Override
    public int getCurrentPageNo() {
        return pageIndex + 1;
    }

    /**
     * See TIKA-2845 for why we need to override this.
     *
     * @param pages
     * @throws IOException
     */
    @Override
    protected void processPages(PDPageTree pages) throws IOException {
        //we currently need this hack because we aren't able to increment
        //the private currentPageNo in PDFTextStripper,
        //and PDFTextStripper's processPage relies on that variable
        //being >= startPage when deciding whether or not to process a page
        // See:
        // if (currentPageNo >= startPage && currentPageNo <= endPage
        //                && (startBookmarkPageNumber == -1 || currentPageNo >= startBookmarkPageNumber)
        //                && (endBookmarkPageNumber == -1 || currentPageNo <= endBookmarkPageNumber))
        //        {
        super.setStartPage(-1);
        for (PDPage page : pages) {
            if (getCurrentPageNo() >= getStartPage()
                    && getCurrentPageNo() <= getEndPage()) {
                processPage(page);
            }
            pageIndex++;
        }
    }

    @Override
    public void setStartBookmark(PDOutlineItem pdOutlineItem) {
        throw new UnsupportedOperationException("We don't currently support this -- See PDFTextStripper's processPages() for how to implement this.");
    }

    @Override
    public void setEndBookmark(PDOutlineItem pdOutlineItem) {
        throw new UnsupportedOperationException("We don't currently support this -- See PDFTextStripper's processPages() for how to implement this.");
    }

    @Override
    public void setStartPage(int startPage) {
        this.startPage = startPage;
    }

    @Override
    public int getStartPage() {
        return startPage;
    }

    @Override
    protected void showGlyph(Matrix textRenderingMatrix, PDFont font, int code, String unicode, Vector displacement) throws IOException
    {
        super.showGlyph(textRenderingMatrix, font, code, unicode, displacement);
        if (unicode == null || unicode.isEmpty()) {
            unmappedUnicodeCharsPerPage++;
        }
        totalCharsPerPage++;
    }
}
