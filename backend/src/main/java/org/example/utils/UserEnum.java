package org.example.utils;

/**
 * 用户相关枚举
 */
public enum UserEnum {
    /** Redis 中用户 Token 的 key 前缀 */
    USER_TOKEN("user_token");

    private final String value;

    UserEnum(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
