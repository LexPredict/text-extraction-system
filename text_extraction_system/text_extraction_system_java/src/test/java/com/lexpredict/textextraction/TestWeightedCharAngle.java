package com.lexpredict.textextraction;

import junit.framework.TestCase;

import java.util.ArrayList;
import java.util.Arrays;

public class TestWeightedCharAngle extends TestCase {
    public void testSimplyWeighted() throws Exception {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(0, 10, 0),
                new WeightedCharAngle(10, 990, 0)
        };
        float a = WeightedCharAngle.getWeightedAverage(angles, 0);
        a = Math.round(a * 1000) / 1000f;
        assertEquals(a, 9.9f);
    }

    public void testEquidistant() throws Exception {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(1, 10, 0),
                new WeightedCharAngle(5, 500, 0),
                new WeightedCharAngle(6, 500, 0),
                new WeightedCharAngle(100, 10, 0),
        };
        float a = WeightedCharAngle.getWeightedAverage(angles, 0.1f);
        a = Math.round(a * 10) / 10f;
        assertEquals(a, 5.5f);

        float b = WeightedCharAngle.getWeightedAverage(angles, 0);
        assertTrue(b > a);
    }

    public void testDistantTails() throws Exception {
        WeightedCharAngle[] angles = {
                new WeightedCharAngle(1, 10, 0),
                new WeightedCharAngle(5, 500, 0),
                new WeightedCharAngle(6, 500, 0),
                new WeightedCharAngle(100, 10, 0),
        };
        float a0 = WeightedCharAngle.getWeightedAverage(angles, 0.1f);

        float[] meanValues = { 3, 7 };
        ArrayList<Float> avAngles = new ArrayList<>();
        for (float mean: meanValues) {
            for (WeightedCharAngle a: angles)
                a.distance = Math.abs(a.angle - mean);
            float aM = WeightedCharAngle.getWeightedAverage(angles, 0.1f);
            avAngles.add(aM);
        }
        assertTrue(avAngles.get(0) < a0);
        assertTrue(avAngles.get(1) > a0);
    }
}
