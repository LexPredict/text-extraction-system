package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PDFPlainText;
import junit.framework.TestCase;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.File;
import java.util.ArrayList;

public class TestWeightedCharAngle extends TestCase {
    public void testWrongAngle6() throws Exception {
        try (PDDocument document =
                     PDDocument.load(new File("/home/andrey/Downloads/df_page_2.pdf"))) {
            PDFPlainText res = PDFToTextWithCoordinates.process(document, true);
            document.save("/tmp/000.pdf");
            GetTextFromPDF.renderDebugPDF(document, res, "/tmp/111.pdf");
        }
    }


    public void testSimplyWeighted() {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(0, 10, 0),
                new WeightedCharAngle(10, 990, 0)
        };
        float a = WeightedCharAngle.getWeightedAverage(angles, 0)[0];
        a = Math.round(a * 1000) / 1000f;
        assertEquals(a, 9.9f);
    }

    public void testEquidistant() {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(1, 10, 0),
                new WeightedCharAngle(5, 500, 0),
                new WeightedCharAngle(6, 500, 0),
                new WeightedCharAngle(100, 10, 0),
        };
        float a = WeightedCharAngle.getWeightedAverage(angles, 0.1f)[0];
        a = Math.round(a * 10) / 10f;
        assertEquals(a, 5.5f);

        float b = WeightedCharAngle.getWeightedAverage(angles, 0)[0];
        assertTrue(b > a);
    }

    public void testDistantTails() {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(1, 10, 0),
                new WeightedCharAngle(5, 500, 0),
                new WeightedCharAngle(6, 500, 0),
                new WeightedCharAngle(100, 10, 0),
        };
        float a0 = WeightedCharAngle.getWeightedAverage(angles, 0.1f)[0];

        float[] meanValues = { 3, 7 };
        ArrayList<Float> avAngles = new ArrayList<>();
        for (float mean: meanValues) {
            for (WeightedCharAngle a: angles)
                a.distance = Math.abs(a.angle - mean);
            float aM = WeightedCharAngle.getWeightedAverage(angles, 0.1f)[0];
            avAngles.add(aM);
        }
        assertTrue(avAngles.get(0) < a0);
        assertTrue(avAngles.get(1) > a0);
    }

    public void testStandardDeviationOk() {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(1, 5, 0),
                new WeightedCharAngle(89, 500, 0),
                new WeightedCharAngle(91, 500, 0),
                new WeightedCharAngle(180, 4, 0),
                new WeightedCharAngle(1270, 1, 0),
        };
        for (WeightedCharAngle angle: angles)
            angle.distance = Math.abs(angle.angle - 90);
        float []angleDev = WeightedCharAngle.getWeightedAverage(angles, 0.05f);
        assertEquals(90, (int)Math.round(angleDev[0]));
        assertTrue(angleDev[1] < 1);

        // without cutting tails mean deviation is a larger value
        angleDev = WeightedCharAngle.getWeightedAverage(angles, 0.001f);
        assertTrue(angleDev[1] > 1);
    }

    public void testTwoValues() {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(0, 1149, 0),
                new WeightedCharAngle(88.9f, 12, 0)
        };
        for (WeightedCharAngle angle: angles)
            angle.distance = Math.abs(angle.angle);
        float []angleDev = WeightedCharAngle.getWeightedAverage(angles, 0.05f);
        assertTrue(angleDev[0] < 0.2f);
    }
}
