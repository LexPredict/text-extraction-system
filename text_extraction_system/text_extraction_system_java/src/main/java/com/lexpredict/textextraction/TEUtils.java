package com.lexpredict.textextraction;

import org.apache.commons.lang3.StringUtils;

public class TEUtils {
    private TEUtils(){}

    public static boolean containsAlphaNumeric(String s) {
        for (int i = 0; i < s.length(); i++) {
            if (Character.isLetterOrDigit(s.charAt(i)))
                return true;
        }
        return false;
    }
}
