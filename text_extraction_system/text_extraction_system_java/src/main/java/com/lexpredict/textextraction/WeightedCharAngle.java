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

    public static boolean checkStandardDeviationOk(
            WeightedCharAngle[] items,
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
        // absolute deviation works better for small angles but much worse for relatively big ones
        // that's why we use here:
        // - absolute deviation
        // - but compare this value to expected maximum deviation that roughly equals to mean^2:
        // exMaxDev ~ 0.2 for mean = 0, 0.5 for mean = 1 ... 6.5 for mean = 90
        float ma = Math.abs(mean);
        double exMaxDev = Math.pow((ma + 0.32) * 0.25, 0.5);
        return meanDev < exMaxDev;
    }
}