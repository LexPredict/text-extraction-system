package com.lexpredict.textextraction;

public class WeightedCharAngle {
    public final float angle;
    public final int count;
    public float distance;

    public WeightedCharAngle(float angle, int count, float distance) {
        this.angle = angle;
        this.count = count;
        this.distance = distance;
    }

    public static float getWeightedAverage(WeightedCharAngle[] items, int startIndex) {
        float sum = 0;
        int count = 0;
        for (int i = startIndex; i < items.length; i++) {
            WeightedCharAngle item = items[i];
            sum += item.angle * item.count;
            count += item.count;
        }
        return sum / count;
    }

    public static float getStandardDeviation(WeightedCharAngle[] items,
                                             float mean) {
        float sum = 0;
        int count = 0;
        for (WeightedCharAngle item: items) {
            float delta = item.angle - mean;
            delta = delta * delta;
            sum += delta * item.count;
            count += item.count;
        }
        double meanDev = Math.pow(sum / count, 0.5F);
        return (float) meanDev;
    }
}