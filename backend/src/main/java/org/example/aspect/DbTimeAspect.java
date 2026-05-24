package org.example.aspect;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Slf4j
@Aspect
@Component
public class DbTimeAspect {

    // 颜色代码（ANSI 编码）
    private static final String GREEN = "\u001B[32m";
    private static final String YELLOW = "\u001B[33m";
    private static final String RED = "\u001B[31m";
    private static final String RESET = "\u001B[0m";

    @Around("execution(* org.example.mapper..*.*(..))")
    public Object countDbTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = joinPoint.proceed();
        long cost = System.currentTimeMillis() - start;

        String className = joinPoint.getSignature().getDeclaringType().getSimpleName();
        String methodName = joinPoint.getSignature().getName();
        String methodFull = className + "." + methodName;

        // 根据耗时自动变色并格式化输出
        if (cost > 500) {
            // 超过500ms → 红色警告
            log.info("\n{}━━━━━━━━━ [慢SQL警告] ━━━━━━━━━" + RESET,
                    RED);
            log.info("{}⚠️  方法: {}" + RESET, RED, methodFull);
            log.info("{}⏱  耗时: {} ms" + RESET, RED, cost);
            log.info("{}🔍 返回: {}" + RESET, RED, result != null ? result.getClass().getSimpleName() : "null");
            log.info("{}━━━━━━━━━━━━━━━━━━━━━━━" + RESET + "\n", RED);
        } else if (cost > 200) {
            // 200~500ms → 黄色提醒
            log.info("\n{}━━━━ [数据库操作] ━━━━" + RESET,
                    YELLOW);
            log.info("{}📊 方法: {}" + RESET, YELLOW, methodFull);
            log.info("{}⏱  耗时: {} ms" + RESET, YELLOW, cost);
            log.info("{}━━━━━━━━━━━━━━━━" + RESET + "\n", YELLOW);
        }

        return result;
    }
}