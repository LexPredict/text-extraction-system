package com.lexpredict.textextraction;

import java.util.Arrays;

public class WeightedCharAngle {
    public final float angle;
    public final float count;
    public float distance;

    public WeightedCharAngle(float angle, float count, float distance) {
        this.angle = angle;
        this.count = count;
        this.distance = distance;
    }

    @Override
    public String toString() {
        return String.format("%.2f x%.1f, d=%.2f", this.angle, this.count, this.distance);
    }

    public static float getWeightedAverage(WeightedCharAngle[] items,
                                           float tailsSkipQuantile) {
        if (items.length == 0)
            return 0;
        if (items.length == 1)
            return items[0].angle;

        float sumW = Arrays.stream(items).map(it -> it.count).reduce(0f, Float::sum);

        WeightedCharAngle[] wItems = new WeightedCharAngle[items.length];
        for (int i = 0; i < items.length; i++)
            wItems[i] = new WeightedCharAngle(items[i].angle, items[i].count / sumW, items[i].distance);

        if (tailsSkipQuantile == 0 || wItems.length < 3)
            return Arrays.stream(wItems).map(it -> it.angle * it.count).reduce(0f, Float::sum);

        // we cut 2*N% of extremely distant values
        // if all distances are 0 - we cut N% of extremely low and N% of extremely high values
        boolean equidistant = true;
        for (WeightedCharAngle item: wItems)
            if (item.distance != 0) {
                equidistant = false;
                break;
            }
        if (equidistant) {
            Arrays.sort(wItems, (a, b) -> Float.compare(a.angle, b.angle));
            return skipTailsEquidistant(tailsSkipQuantile, tailsSkipQuantile, wItems);
        }
        // sort by distance and cut 2*N% of extremely distant values (tail)
        Arrays.sort(wItems, (WeightedCharAngle a, WeightedCharAngle b) -> Float.compare(a.distance, b.distance));
        return skipTailsEquidistant(0, tailsSkipQuantile * 2, wItems);
    }

    private static float skipTailsEquidistant(float headSkipQuantile,
                                              float tailSkipQuantile,
                                              WeightedCharAngle[] wItems) {
        // cut N% of extremely low and N% of extremely high values
        // the array is already sorted
        float tailW = 1 - tailSkipQuantile;
        float bodyW = 1 - headSkipQuantile - tailSkipQuantile;
        float accumWeight = 0, sumVal = 0;
        boolean passedHead = false, passedTail = false;

        for (WeightedCharAngle item: wItems) {
            float w = item.count;
            accumWeight += w;
            if (!passedHead) {
                if (accumWeight < headSkipQuantile) continue;
                w = accumWeight - headSkipQuantile;
                passedHead = true;
            }
            if (accumWeight > tailW) {
                float ex_part = accumWeight - tailW;
                w -= ex_part;
                passedTail = true;
            }
            float share = w / bodyW;
            sumVal += item.angle * share;
            if (passedTail) break;
        }
        return sumVal;
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