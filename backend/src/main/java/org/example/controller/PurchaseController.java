package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.context.UserContextHolder;
import org.example.service.PurchaseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 购买测试控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/purchase")
public class PurchaseController {
    
    @Autowired
    private PurchaseService purchaseService;
    
    /**
     * 同步购买接口（用于性能测试）
     */
    @PostMapping("/sync/{storeBookId}")
    public Result purchaseBookSync(@PathVariable Long storeBookId) {
        long startTime = System.currentTimeMillis();
        
        try {
            Long userId = UserContextHolder.getUserId();
            log.info("🔄 [同步购买测试] 开始 | 用户ID: {} | 商店书ID: {}", userId, storeBookId);
            
            Long userBookId = purchaseService.purchaseBookSync(userId, storeBookId);
            
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            
            log.info("✅ [同步购买测试] 完成 | 用户ID: {} | 商店书ID: {} | 用户书ID: {} | 总耗时: {}ms", 
                    userId, storeBookId, userBookId, duration);
            
            return Result.success("同步购买成功", userBookId);
        } catch (Exception e) {
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            
            log.error("❌ [同步购买测试] 失败 | 耗时: {}ms", duration, e);
            return Result.error("同步购买失败: " + e.getMessage());
        }
    }
    
    /**
     * 异步购买接口（用于性能测试）
     */
    @PostMapping("/async/{storeBookId}")
    public Result purchaseBookAsync(@PathVariable Long storeBookId) {
        long startTime = System.currentTimeMillis();
        
        try {
            Long userId = UserContextHolder.getUserId();
            log.info("⚡ [异步购买测试] 开始 | 用户ID: {} | 商店书ID: {}", userId, storeBookId);
            
            Long userBookId = purchaseService.purchaseBookAsync(userId, storeBookId);
            
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            
            log.info("✅ [异步购买测试] 完成 | 用户ID: {} | 商店书ID: {} | 用户书ID: {} | 关键路径耗时: {}ms", 
                    userId, storeBookId, userBookId, duration);
            
            return Result.success("异步购买成功，后台正在处理单词复制等操作", userBookId);
        } catch (Exception e) {
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            
            log.error("❌ [异步购买测试] 失败 | 耗时: {}ms", duration, e);
            return Result.error("异步购买失败: " + e.getMessage());
        }
    }
}
