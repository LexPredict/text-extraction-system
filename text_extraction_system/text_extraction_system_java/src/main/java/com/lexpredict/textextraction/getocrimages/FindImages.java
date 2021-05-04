package com.lexpredict.textextraction.getocrimages;

import org.apache.pdfbox.contentstream.PDFStreamEngine;
import org.apache.pdfbox.contentstream.operator.DrawObject;
import org.apache.pdfbox.contentstream.operator.Operator;
import org.apache.pdfbox.contentstream.operator.OperatorName;
import org.apache.pdfbox.contentstream.operator.state.*;
import org.apache.pdfbox.cos.COSBase;
import org.apache.pdfbox.cos.COSName;
import org.apache.pdfbox.pdmodel.graphics.PDXObject;
import org.apache.pdfbox.pdmodel.graphics.form.PDFormXObject;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;
import org.apache.pdfbox.util.Matrix;

import java.awt.*;
import java.awt.geom.Rectangle2D;
import java.io.IOException;
import java.util.LinkedList;
import java.util.List;

public class FindImages extends PDFStreamEngine {

    public static class FoundImage {
        public final PDImageXObject imageXObject;

        public final Matrix matrix;

        public final Shape shape;

        public final Rectangle2D bounds;


        public FoundImage(PDImageXObject imageXObject, Matrix matrix) {
            this.imageXObject = imageXObject;
            this.matrix = matrix;
            Rectangle2D.Double origBounds = new Rectangle2D.Double(0, 0, 1, 1);
            this.shape = matrix.createAffineTransform().createTransformedShape(origBounds);
            this.bounds = this.shape.getBounds2D();
        }
    }

    public List<FoundImage> found = new LinkedList<>();

    public FindImages() throws IOException {
        addOperator(new Concatenate());
        addOperator(new DrawObject());
        addOperator(new SetGraphicsStateParameters());
        addOperator(new Save());
        addOperator(new Restore());
        addOperator(new SetMatrix());
    }

    @Override
    protected void processOperator(Operator operator, List<COSBase> operands) throws IOException {
        String operation = operator.getName();
        if (OperatorName.DRAW_OBJECT.equals(operation)) {
            COSName objectName = (COSName) operands.get(0);
            PDXObject xobject = getResources().getXObject(objectName);
            if (xobject instanceof PDImageXObject) {
                PDImageXObject image = (PDImageXObject) xobject;
                Matrix ctmNew = getGraphicsState().getCurrentTransformationMatrix();

                this.found.add(new FoundImage(image, ctmNew));
            } else if (xobject instanceof PDFormXObject) {
                PDFormXObject form = (PDFormXObject) xobject;
                showForm(form);
            }
        } else {
            super.processOperator(operator, operands);
        }
    }

}
