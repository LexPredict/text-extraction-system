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

import org.apache.pdfbox.cos.COSArray;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import org.apache.pdfbox.util.Matrix;
import org.xml.sax.SAXException;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.Writer;
import java.util.*;


class PDF2Text extends AbstractPDF2Text {
    private static final List<String> JPEG = Arrays.asList(
            COSName.DCT_DECODE.getName(),
            COSName.DCT_DECODE_ABBREVIATION.getName());

    private static final List<String> JP2 =
            Arrays.asList(COSName.JPX_DECODE.getName());

    private static final List<String> JB2 = Arrays.asList(
            COSName.JBIG2_DECODE.getName());

    private PDF2Text(PDDocument document,
                     OutputStream fwText,
                     OutputStream fwCoords,
                     OutputStream fwPages)
            throws IOException {
        super(document, fwText, fwCoords, fwPages);
    }

    /**
     * Converts the given PDF document (and related metadata) to a stream
     * of XHTML SAX events sent to the given content handler.
     *
     * @param document PDF document
     * @throws SAXException  if the content handler fails to process SAX events
     * @throws Exception if there was an exception outside of per page processing
     */
    public static void process(
            PDDocument document,
            FileOutputStream fwText,
            FileOutputStream fwCoords,
            FileOutputStream fwPages)
            throws Exception {
        PDF2Text PDF2Text = null;
        try {
            // Extract text using a dummy Writer as we override the
            // key methods to output to the given content
            // handler.
            PDF2Text = new PDF2Text.AngleDetectingPDF2Text(document, fwText, fwCoords, fwPages);
            // PDF2Text = new PDF2Text(document, handler, context, metadata, config);
            PDF2Text.writeText(document, new Writer() {
                @Override
                public void write(char[] cbuf, int off, int len) {
                }

                @Override
                public void flush() {
                }

                @Override
                public void close() {
                }
            });
        } catch (IOException e) {
            if (e.getCause() instanceof SAXException) {
                throw (SAXException) e.getCause();
            } else {
                throw new Exception("Unable to extract PDF content", e);
            }
        }
        if (PDF2Text.exceptions.size() > 0) {
            //throw the first
            throw new Exception("Unable to extract PDF content", PDF2Text.exceptions.get(0));
        }
    }

    @Override
    protected void endPage(PDPage page) throws IOException {
        writeParagraphEnd();
        super.endPage(page);
    }

    @Override
    protected void writeParagraphStart() throws IOException {
        super.writeParagraphStart();
        // TODO: write paragraph coords somewhere?
    }

    @Override
    protected void writeParagraphEnd() throws IOException {
        super.writeParagraphEnd();
        // TODO: write paragraph coords somewhere?
    }

    @Override
    protected void writeString(String text) throws IOException {
        writeToBuffer(text, this.fwText, false);
    }

    @Override
    protected void writeString(String text, List<TextPosition> textPositions) throws IOException
    {
        writeToBuffer(text, this.fwText, false);
        if (textPositions.size() > 0) {
            for (TextPosition pos : textPositions)
                this.writeToBuffer(formatFloatNumbers(";",
                        pageIndex,
                        pos.getX(), pos.getY(),
                        pos.getWidth(), pos.getHeight()), fwCoords, true);
        }
    }

    @Override
    protected void writeCharacters(TextPosition text) throws IOException {
        writeToBuffer(text.getUnicode(), this.fwText, false);
    }

    @Override
    protected void writeWordSeparator() throws IOException {
        writeToBuffer(getWordSeparator(), this.fwText, false);
    }

    @Override
    protected void writeLineSeparator() throws IOException {
        writeToBuffer("\n", this.fwText, false);
    }

    class AngleCollector extends PDFTextStripper {
        Set<Integer> angles = new HashSet<>();

        public Set<Integer> getAngles() {
            return angles;
        }

        /**
         * Instantiate a new PDFTextStripper object.
         *
         * @throws IOException If there is an error loading the properties.
         */
        AngleCollector() throws IOException {
        }

        @Override
        protected void processTextPosition(TextPosition text) {
            Matrix m = text.getTextMatrix();
            m.concatenate(text.getFont().getFontMatrix());
            int angle = (int) Math.round(Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY())));
            angle = (angle + 360) % 360;
            angles.add(angle);
        }
    }

    private static class AngleDetectingPDF2Text extends PDF2Text {

        private AngleDetectingPDF2Text(PDDocument document,
                                       FileOutputStream fwText,
                                       FileOutputStream fwCoords,
                                       FileOutputStream fwPages) throws IOException {
            super(document, fwText, fwCoords, fwPages);
        }

        @Override
        protected void startPage(PDPage page) throws IOException {
            //no-op
        }

        @Override
        protected void endPage(PDPage page) throws IOException {
            //no-op
        }

        @Override
        public void processPage(PDPage page) throws IOException {
            try {
                super.startPage(page);
                detectAnglesAndProcessPage(page);
            } finally {
                super.endPage(page);
            }
        }

        private void detectAnglesAndProcessPage(PDPage page) throws IOException {
            //copied and pasted from https://issues.apache.org/jira/secure/attachment/12947452/ExtractAngledText.java
            //PDFBOX-4371
            PDF2Text.AngleCollector angleCollector = new PDF2Text.AngleCollector(); // alternatively, reset angles
            angleCollector.setStartPage(getCurrentPageNo());
            angleCollector.setEndPage(getCurrentPageNo());
            angleCollector.getText(document);

            int rotation = page.getRotation();
            page.setRotation(0);

            for (Integer angle : angleCollector.getAngles()) {
                if (angle == 0) {
                    super.processPage(page);
                } else {
                    // prepend a transformation
                    try (PDPageContentStream cs = new PDPageContentStream(document,
                            page, PDPageContentStream.AppendMode.PREPEND, false)) {
                        cs.transform(Matrix.getRotateInstance(-Math.toRadians(angle), 0, 0));
                    }
                    super.processPage(page);
                    // remove transformation
                    COSArray contents = (COSArray) page.getCOSObject().getItem(COSName.CONTENTS);
                    contents.remove(0);
                }
            }
            page.setRotation(rotation);
        }

        @Override
        protected void processTextPosition(TextPosition text) {
            Matrix m = text.getTextMatrix();
            m.concatenate(text.getFont().getFontMatrix());
            int angle = (int) Math.round(Math.toDegrees(Math.atan2(m.getShearY(), m.getScaleY())));
            if (angle == 0) {
                super.processTextPosition(text);
            }
        }
    }
}

