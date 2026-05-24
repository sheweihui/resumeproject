package org.example.service;

/**
 * 秒杀服务接口
 */
public interface SeckillService {
    
    /**
     * 执行秒杀（同步方式）
     */
    String executeSeckillSync(Long userId, Long activityId);
    
    /**
     * 执行秒杀（异步方式 - 推荐）
     */
    String executeSeckillAsync(Long userId, Long activityId);
}
