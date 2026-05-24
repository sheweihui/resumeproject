package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.utils.RedisUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 缓存测试控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/cache")
public class CacheTestController {
    
    @Autowired
    private RedisUtil redisUtil;
    
    /**
     * 测试获取用户缓存数据
     */
    @GetMapping("/user/{userId}")
    public Result testUserCache(@PathVariable Long userId) {
        try {
            log.info("🔍 [缓存测试] 查询用户缓存数据 | 用户ID: {}", userId);
            
            // 获取单词本列表缓存
            String vocabBooksKey = "user:cache:vocab_books:" + userId;
            Object vocabBooks = redisUtil.get(vocabBooksKey);
            
            // 获取所有单词本中的单词缓存
            // 这里需要根据实际的单词本ID来获取，简化处理
            
            Map<String, Object> cacheData = Map.of(
                "vocabBooksKey", vocabBooksKey,
                "vocabBooks", vocabBooks != null ? vocabBooks : "未找到缓存"
            );
            
            log.info("✅ [缓存测试] 查询成功 | 用户ID: {}", userId);
            return Result.success(cacheData);
        } catch (Exception e) {
            log.error("❌ [缓存测试] 查询失败 | 用户ID: {} | 错误: {}", userId, e.getMessage(), e);
            return Result.error("查询缓存失败");
        }
    }
    
    /**
     * 清除用户缓存数据
     */
    @DeleteMapping("/user/{userId}")
    public Result clearUserCache(@PathVariable Long userId) {
        try {
            log.info("🗑️  [缓存测试] 清除用户缓存数据 | 用户ID: {}", userId);
            
            // 清除单词本列表缓存
            String vocabBooksKey = "user:cache:vocab_books:" + userId;
            redisUtil.delete(vocabBooksKey);
            
            log.info("✅ [缓存测试] 清除成功 | 用户ID: {}", userId);
            return Result.success("缓存清除成功");
        } catch (Exception e) {
            log.error("❌ [缓存测试] 清除失败 | 用户ID: {} | 错误: {}", userId, e.getMessage(), e);
            return Result.error("清除缓存失败");
        }
    }
}
