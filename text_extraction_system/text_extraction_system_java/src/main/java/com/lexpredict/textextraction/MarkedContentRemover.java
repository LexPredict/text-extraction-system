package com.lexpredict.textextraction;

import org.apache.pdfbox.contentstream.operator.Operator;
import org.apache.pdfbox.contentstream.operator.OperatorName;
import org.apache.pdfbox.cos.COSDictionary;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdfparser.PDFStreamParser;
import org.apache.pdfbox.pdfwriter.ContentStreamWriter;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDResources;
import org.apache.pdfbox.pdmodel.common.PDStream;

import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


public class MarkedContentRemover {
    public interface MarkedContentMatcher {
        public boolean matches(COSName contentId, COSDictionary props);
    }

    private final MarkedContentMatcher matcher;

    /**
     *
     */
    public MarkedContentRemover(MarkedContentMatcher matcher) {
        this.matcher = matcher;
    }

    public int removeMarkedContent(PDDocument doc, PDPage page) throws IOException {
        ResourceSuppressionTracker resourceSuppressionTracker = new ResourceSuppressionTracker();

        PDResources pdResources = page.getResources();

        PDFStreamParser pdParser = new PDFStreamParser(page);


        PDStream newContents = new PDStream(doc);
        OutputStream newContentOutput = newContents.createOutputStream(COSName.FLATE_DECODE);
        ContentStreamWriter newContentWriter = new ContentStreamWriter(newContentOutput);

        List<Object> operands = new ArrayList<>();
        Operator operator = null;
        Object token;
        int suppressDepth = 0;
        boolean resumeOutputOnNextOperator = false;
        int removedCount = 0;

        while (true) {

            operands.clear();
            token = pdParser.parseNextToken();
            while(token != null && !(token instanceof Operator)) {
                operands.add(token);
                token = pdParser.parseNextToken();
            }
            operator = (Operator)token;

            if (operator == null) break;

            if (resumeOutputOnNextOperator) {
                resumeOutputOnNextOperator = false;
                suppressDepth--;
                if (suppressDepth == 0)
                    removedCount++;
            }

            if (OperatorName.BEGIN_MARKED_CONTENT_SEQ.equals(operator.getName())
                    || OperatorName.BEGIN_MARKED_CONTENT.equals(operator.getName())) {

                COSName contentId = (COSName)operands.get(0);

                final COSDictionary properties;
                if (operands.size() > 1) {
                    Object propsOperand = operands.get(1);

                    if (propsOperand instanceof COSDictionary) {
                        properties = (COSDictionary) propsOperand;

                    } else if (propsOperand instanceof COSName) {
                        properties = pdResources.getProperties((COSName)propsOperand).getCOSObject();
                    } else {
                        properties = new COSDictionary();
                    }
                } else {
                    properties = new COSDictionary();
                }

                if (matcher.matches(contentId, properties)) {
                    suppressDepth++;
                }

            }

            if (OperatorName.END_MARKED_CONTENT.equals(operator.getName())) {
                if (suppressDepth > 0)
                    resumeOutputOnNextOperator = true;
            }

            else if (OperatorName.SET_GRAPHICS_STATE_PARAMS.equals(operator.getName())) {
                resourceSuppressionTracker.markForOperator(COSName.EXT_G_STATE, operands.get(0), suppressDepth == 0);
            }

            else if (OperatorName.DRAW_OBJECT.equals(operator.getName())) {
                resourceSuppressionTracker.markForOperator(COSName.XOBJECT, operands.get(0), suppressDepth == 0);
            }

            else if (OperatorName.SET_FONT_AND_SIZE.equals(operator.getName())) {
                resourceSuppressionTracker.markForOperator(COSName.FONT, operands.get(0), suppressDepth == 0);
            }



            if (suppressDepth == 0) {
                newContentWriter.writeTokens(operands);
                newContentWriter.writeTokens(operator);
            }

        }

        if (resumeOutputOnNextOperator)
            removedCount++;



        newContentOutput.close();

        page.setContents(newContents);

        resourceSuppressionTracker.updateResources(pdResources);

        return removedCount;
    }


    private static class ResourceSuppressionTracker{
        // if the boolean is TRUE, then the resource should be removed.  If the boolean is FALSE, the resource should not be removed
        private final Map<COSName, Map<COSName, Boolean>> tracker = new HashMap<>();

        public void markForOperator(COSName resourceType, Object resourceNameOperand, boolean preserve) {
            if (!(resourceNameOperand instanceof COSName)) return;
            if (preserve) {
                markForPreservation(resourceType, (COSName)resourceNameOperand);
            } else {
                markForRemoval(resourceType, (COSName)resourceNameOperand);
            }
        }

        public void markForRemoval(COSName resourceType, COSName refId) {
            if (!resourceIsPreserved(resourceType, refId)) {
                getResourceTracker(resourceType).put(refId, Boolean.TRUE);
            }
        }

        public void markForPreservation(COSName resourceType, COSName refId) {
            getResourceTracker(resourceType).put(refId, Boolean.FALSE);
        }

        public void updateResources(PDResources pdResources) {
            for (Map.Entry<COSName, Map<COSName, Boolean>> resourceEntry : tracker.entrySet()) {
                for(Map.Entry<COSName, Boolean> refEntry : resourceEntry.getValue().entrySet()) {
                    if (refEntry.getValue().equals(Boolean.TRUE)) {
                        pdResources.getCOSObject().getCOSDictionary(COSName.XOBJECT).removeItem(refEntry.getKey());
                    }
                }
            }
        }

        private boolean resourceIsPreserved(COSName resourceType, COSName refId) {
            return getResourceTracker(resourceType).getOrDefault(refId, Boolean.FALSE);
        }

        private Map<COSName, Boolean> getResourceTracker(COSName resourceType){
            if (!tracker.containsKey(resourceType)) {
                tracker.put(resourceType, new HashMap<>());
            }

            return tracker.get(resourceType);

        }
    }
}