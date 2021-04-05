package com.lexpredict.textextraction.mergepdf;

public class T {

    public static void main(String[] args) {
        double rotate = -88.1234;

        int pageRotate = -90 * (int) Math.round(rotate / 90d);
        double contentsRotate = rotate + pageRotate;

        System.out.println(pageRotate);
        System.out.println(contentsRotate);
        System.out.println(360%180);
    }
}
