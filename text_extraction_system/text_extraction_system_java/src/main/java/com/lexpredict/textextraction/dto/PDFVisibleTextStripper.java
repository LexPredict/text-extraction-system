package com.lexpredict.textextraction.dto;

import java.awt.geom.Area;
import java.awt.geom.GeneralPath;
import java.awt.geom.Point2D;
import java.io.IOException;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;

import org.apache.pdfbox.contentstream.operator.MissingOperandException;
import org.apache.pdfbox.contentstream.operator.Operator;
import org.apache.pdfbox.contentstream.operator.OperatorProcessor;
import org.apache.pdfbox.cos.COSBase;
import org.apache.pdfbox.cos.COSNumber;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.graphics.state.PDGraphicsState;
import org.apache.pdfbox.rendering.PageDrawer;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import org.apache.pdfbox.util.Matrix;
import org.apache.pdfbox.util.Vector;

// Remove invisible text from pdf using pdfbox
// This class extends the {@link PDFTextStripper} to ignore text hidden by clipping or by covering
// with a filled path.
// The PDFTextStripper does not implement call backs for path related instructions but
// the PageDrawer does. So we borrow code from there to implement path related behavior here.
public class PDFVisibleTextStripper extends PDFTextStripper {
    private boolean checkEndPointToo = false;
    private boolean useFatGlyphOrigin = false;
    private PrintStream dropStream = null;

    public PDFVisibleTextStripper() throws IOException {
        this(false);
    }

    public PDFVisibleTextStripper(boolean checkEndPointToo) throws IOException {
        this(checkEndPointToo, null);
    }

    // checkEndPointToo flag whether to also check the end point of the character baseline for
    // visibility; if true, the conditions for visibility of a character are stricter, but
    // unfortunately the calculation of the character baseline end point only work correctly
    // for unrotated text.
    public PDFVisibleTextStripper(boolean checkEndPointToo, PrintStream dropStream) throws IOException {
        this.checkEndPointToo = checkEndPointToo;
        this.dropStream = dropStream;

        addOperator(new AppendRectangleToPath());
        addOperator(new ClipEvenOddRule());
        addOperator(new ClipNonZeroRule());
        addOperator(new ClosePath());
        addOperator(new CurveTo());
        addOperator(new CurveToReplicateFinalPoint());
        addOperator(new CurveToReplicateInitialPoint());
        addOperator(new EndPath());
        addOperator(new FillEvenOddAndStrokePath());
        addOperator(new FillEvenOddRule());
        addOperator(new FillNonZeroAndStrokePath());
        addOperator(new FillNonZeroRule());
        addOperator(new LineTo());
        addOperator(new MoveTo());
        addOperator(new StrokePath());
    }

    public void setUseFatGlyphOrigin(boolean useFatGlyphOrigin) {
        this.useFatGlyphOrigin = useFatGlyphOrigin;
    }

    float lowerLeftX = 0;
    float lowerLeftY = 0;

    @Override
    public void processPage(PDPage page) throws IOException {
        PDRectangle pageSize = page.getCropBox();

        lowerLeftX = pageSize.getLowerLeftX();
        lowerLeftY = pageSize.getLowerLeftY();

        super.processPage(page);
    }

    @Override
    protected void processTextPosition(TextPosition text) {
        Matrix textMatrix = text.getTextMatrix();
        Vector start = textMatrix.transform(new Vector(0, 0));
        Vector end = new Vector(start.getX() + text.getWidth(), start.getY());

        PDGraphicsState gs = getGraphicsState();
        Area area = gs.getCurrentClippingPath();
        if (area == null ||
                (contains(area, lowerLeftX + start.getX(), lowerLeftY + start.getY()) &&
                        ((!checkEndPointToo) || contains(area, lowerLeftX + end.getX(), lowerLeftY + end.getY()))))
            super.processTextPosition(text);
        else if (dropStream != null)
            dropStream.printf("Clipped '%s' at %s,%s\n", text.getUnicode(), lowerLeftX + start.getX(), lowerLeftY + start.getY());
    }

    // Due to different rounding of numbers in the clip path and text transformations, it can
    // happen that the glyph origin is exactly on the border of the clip path but the
    // Are->contains(double, double) method of the determined clip path returns false for
    // the determined origin coordinates.
    // To fix this, this method generates a small rectangle around the (glyph origin) coordinates
    // and checks whether this rectangle intersects the (clip path) area.
    protected boolean contains(Area area, float x, float y) {
        if (useFatGlyphOrigin) {
            double length = .0002;
            double up = 1.0001;
            double down = .9999;
            return area.intersects(x < 0 ? x*up : x*down, y < 0 ? y*up : y*down, Math.abs(x*length), Math.abs(y*length));
        } else
            return area.contains(x, y);
    }

    private GeneralPath linePath = new GeneralPath();

    void deleteCharsInPath() {
        for (List<TextPosition> list : charactersByArticle) {
            List<TextPosition> toRemove = new ArrayList<>();
            for (TextPosition text : list) {
                Matrix textMatrix = text.getTextMatrix();
                Vector start = textMatrix.transform(new Vector(0, 0));
                Vector end = new Vector(start.getX() + text.getWidth(), start.getY());
                if (linePath.contains(lowerLeftX + start.getX(), lowerLeftY + start.getY()) ||
                        (checkEndPointToo && linePath.contains(lowerLeftX + end.getX(), lowerLeftY + end.getY()))) {
                    toRemove.add(text);
                }
            }
            if (toRemove.size() != 0) {
                System.out.println(toRemove.size());
                list.removeAll(toRemove);
            }
        }
    }

    public final class AppendRectangleToPath extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            if (operands.size() < 4) {
                throw new MissingOperandException(operator, operands);
            }
            if (!checkArrayTypesClass(operands, COSNumber.class)) {
                return;
            }
            COSNumber x = (COSNumber) operands.get(0);
            COSNumber y = (COSNumber) operands.get(1);
            COSNumber w = (COSNumber) operands.get(2);
            COSNumber h = (COSNumber) operands.get(3);

            float x1 = x.floatValue();
            float y1 = y.floatValue();

            // create a pair of coordinates for the transformation
            float x2 = w.floatValue() + x1;
            float y2 = h.floatValue() + y1;

            Point2D p0 = context.transformedPoint(x1, y1);
            Point2D p1 = context.transformedPoint(x2, y1);
            Point2D p2 = context.transformedPoint(x2, y2);
            Point2D p3 = context.transformedPoint(x1, y2);

            // to ensure that the path is created in the right direction, we have to create
            // it by combining single lines instead of creating a simple rectangle
            linePath.moveTo((float) p0.getX(), (float) p0.getY());
            linePath.lineTo((float) p1.getX(), (float) p1.getY());
            linePath.lineTo((float) p2.getX(), (float) p2.getY());
            linePath.lineTo((float) p3.getX(), (float) p3.getY());

            // close the subpath instead of adding the last line so that a possible set line
            // cap style isn't taken into account at the "beginning" of the rectangle
            linePath.closePath();
        }

        @Override
        public String getName() {
            return "re";
        }
    }

    public final class StrokePath extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.reset();
        }

        @Override
        public String getName() {
            return "S";
        }
    }

    public final class FillEvenOddRule extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.setWindingRule(GeneralPath.WIND_EVEN_ODD);
            deleteCharsInPath();
            linePath.reset();
        }

        @Override
        public String getName() {
            return "f*";
        }
    }

    public class FillNonZeroRule extends OperatorProcessor {
        @Override
        public final void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.setWindingRule(GeneralPath.WIND_NON_ZERO);
            deleteCharsInPath();
            linePath.reset();
        }

        @Override
        public String getName() {
            return "f";
        }
    }

    public final class FillEvenOddAndStrokePath extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.setWindingRule(GeneralPath.WIND_EVEN_ODD);
            deleteCharsInPath();
            linePath.reset();
        }

        @Override
        public String getName() {
            return "B*";
        }
    }

    public class FillNonZeroAndStrokePath extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.setWindingRule(GeneralPath.WIND_NON_ZERO);
            deleteCharsInPath();
            linePath.reset();
        }

        @Override
        public String getName() {
            return "B";
        }
    }

    public final class ClipEvenOddRule extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.setWindingRule(GeneralPath.WIND_EVEN_ODD);
            getGraphicsState().intersectClippingPath(linePath);
        }

        @Override
        public String getName() {
            return "W*";
        }
    }

    public class ClipNonZeroRule extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.setWindingRule(GeneralPath.WIND_NON_ZERO);
            getGraphicsState().intersectClippingPath(linePath);
        }

        @Override
        public String getName() {
            return "W";
        }
    }

    public final class MoveTo extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            if (operands.size() < 2) {
                throw new MissingOperandException(operator, operands);
            }
            COSBase base0 = operands.get(0);
            if (!(base0 instanceof COSNumber)) {
                return;
            }
            COSBase base1 = operands.get(1);
            if (!(base1 instanceof COSNumber)) {
                return;
            }
            COSNumber x = (COSNumber) base0;
            COSNumber y = (COSNumber) base1;
            Point2D.Float pos = context.transformedPoint(x.floatValue(), y.floatValue());
            linePath.moveTo(pos.x, pos.y);
        }

        @Override
        public String getName() {
            return "m";
        }
    }

    public class LineTo extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            if (operands.size() < 2) {
                throw new MissingOperandException(operator, operands);
            }
            COSBase base0 = operands.get(0);
            if (!(base0 instanceof COSNumber)) {
                return;
            }
            COSBase base1 = operands.get(1);
            if (!(base1 instanceof COSNumber)) {
                return;
            }
            // append straight line segment from the current point to the point
            COSNumber x = (COSNumber) base0;
            COSNumber y = (COSNumber) base1;

            Point2D.Float pos = context.transformedPoint(x.floatValue(), y.floatValue());

            linePath.lineTo(pos.x, pos.y);
        }

        @Override
        public String getName() {
            return "l";
        }
    }

    public class CurveTo extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            if (operands.size() < 6) {
                throw new MissingOperandException(operator, operands);
            }
            if (!checkArrayTypesClass(operands, COSNumber.class)) {
                return;
            }
            COSNumber x1 = (COSNumber) operands.get(0);
            COSNumber y1 = (COSNumber) operands.get(1);
            COSNumber x2 = (COSNumber) operands.get(2);
            COSNumber y2 = (COSNumber) operands.get(3);
            COSNumber x3 = (COSNumber) operands.get(4);
            COSNumber y3 = (COSNumber) operands.get(5);

            Point2D.Float point1 = context.transformedPoint(x1.floatValue(), y1.floatValue());
            Point2D.Float point2 = context.transformedPoint(x2.floatValue(), y2.floatValue());
            Point2D.Float point3 = context.transformedPoint(x3.floatValue(), y3.floatValue());

            linePath.curveTo(point1.x, point1.y, point2.x, point2.y, point3.x, point3.y);
        }

        @Override
        public String getName() {
            return "c";
        }
    }

    public final class CurveToReplicateFinalPoint extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            if (operands.size() < 4) {
                throw new MissingOperandException(operator, operands);
            }
            if (!checkArrayTypesClass(operands, COSNumber.class)) {
                return;
            }
            COSNumber x1 = (COSNumber) operands.get(0);
            COSNumber y1 = (COSNumber) operands.get(1);
            COSNumber x3 = (COSNumber) operands.get(2);
            COSNumber y3 = (COSNumber) operands.get(3);

            Point2D.Float point1 = context.transformedPoint(x1.floatValue(), y1.floatValue());
            Point2D.Float point3 = context.transformedPoint(x3.floatValue(), y3.floatValue());

            linePath.curveTo(point1.x, point1.y, point3.x, point3.y, point3.x, point3.y);
        }

        @Override
        public String getName() {
            return "y";
        }
    }

    public class CurveToReplicateInitialPoint extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            if (operands.size() < 4) {
                throw new MissingOperandException(operator, operands);
            }
            if (!checkArrayTypesClass(operands, COSNumber.class)) {
                return;
            }
            COSNumber x2 = (COSNumber) operands.get(0);
            COSNumber y2 = (COSNumber) operands.get(1);
            COSNumber x3 = (COSNumber) operands.get(2);
            COSNumber y3 = (COSNumber) operands.get(3);

            Point2D currentPoint = linePath.getCurrentPoint();

            Point2D.Float point2 = context.transformedPoint(x2.floatValue(), y2.floatValue());
            Point2D.Float point3 = context.transformedPoint(x3.floatValue(), y3.floatValue());

            linePath.curveTo((float) currentPoint.getX(), (float) currentPoint.getY(), point2.x, point2.y, point3.x, point3.y);
        }

        @Override
        public String getName() {
            return "v";
        }
    }

    public final class ClosePath extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.closePath();
        }

        @Override
        public String getName() {
            return "h";
        }
    }

    public final class EndPath extends OperatorProcessor {
        @Override
        public void process(Operator operator, List<COSBase> operands) throws IOException {
            linePath.reset();
        }

        @Override
        public String getName() {
            return "n";
        }
    }
}
