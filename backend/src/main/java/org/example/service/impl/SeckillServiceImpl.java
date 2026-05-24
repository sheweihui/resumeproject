package org.example.service.impl;

import lombok.extern.slf4j.Slf4j;
import org.example.entity.SeckillActivity;
import org.example.entity.SeckillMessageLog;
import org.example.entity.SeckillOrder;
import org.example.mapper.SeckillActivityMapper;
import org.example.mapper.SeckillMessageLogMapper;
import org.example.mapper.SeckillOrderMapper;
import org.example.mq.producer.MessageProducer;
import org.example.service.SeckillService;
import org.example.service.UserPointsAccountService;
import org.example.utils.RedisUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * 秒杀服务实现类
 */
@Slf4j
@Service
public class SeckillServiceImpl implements SeckillService {
    
    @Autowired
    private SeckillActivityMapper seckillActivityMapper;
    
    @Autowired
    private SeckillOrderMapper seckillOrderMapper;
    
    @Autowired
    private SeckillMessageLogMapper seckillMessageLogMapper;
    
    @Autowired
    private UserPointsAccountService userPointsAccountService;
    
    @Autowired
    private MessageProducer messageProducer;
    
    @Autowired
    private RedisUtil redisUtil;
    
    private static final String SECKILL_STOCK_KEY = "seckill:stock:";
    private static final String SECKILL_USER_KEY = "seckill:user:";
    
    @Override
    @Transactional
    public String executeSeckillSync(Long userId, Long activityId) {
        long startTime = System.currentTimeMillis();
        log.info("⏱️ [同步秒杀] 开始 | 用户ID: {} | 活动ID: {}", userId, activityId);
        
        // 1. 查询秒杀活动
        SeckillActivity activity = seckillActivityMapper.selectById(activityId);
        if (activity == null) {
            throw new RuntimeException("秒杀活动不存在");
        }
        
        // 2. 校验活动时间
        LocalDateTime now = LocalDateTime.now();
        if (now.isBefore(activity.getStartTime())) {
            throw new RuntimeException("秒杀尚未开始");
        }
        if (now.isAfter(activity.getEndTime())) {
            throw new RuntimeException("秒杀已结束");
        }
        
        // 3. 检查是否已购买
        SeckillOrder existingOrder = seckillOrderMapper.selectByUserAndActivity(userId, activityId);
        if (existingOrder != null) {
            throw new RuntimeException("您已经参与过该秒杀活动");
        }
        
        // 4. 扣减库存（乐观锁）
        int affectedRows = seckillActivityMapper.deductStock(activityId);
        if (affectedRows <= 0) {
            throw new RuntimeException("库存不足，秒杀失败");
        }
        
        // 5. 扣除积分
        userPointsAccountService.deductPoints(
            userId,
            activity.getSeckillPrice(),
            6,
            "秒杀商品",
            activityId
        );
        
        // 6. 创建订单
        String orderNo = generateOrderNo();
        SeckillOrder order = new SeckillOrder();
        order.setUserId(userId);
        order.setActivityId(activityId);
        order.setOrderNo(orderNo);
        
        seckillOrderMapper.insert(order);
        
        long endTime = System.currentTimeMillis();
        log.info("✅ [同步秒杀] 完成 | 用户ID: {} | 订单号: {} | 耗时: {}ms", 
                userId, orderNo, endTime - startTime);
        
        return orderNo;
    }
    
    @Override
    @Transactional
    public String executeSeckillAsync(Long userId, Long activityId) {
        long startTime = System.currentTimeMillis();
        log.info("⚡ [异步秒杀] 开始 | 用户ID: {} | 活动ID: {}", userId, activityId);
        
        // 1. 查询秒杀活动
        SeckillActivity activity = seckillActivityMapper.selectById(activityId);
        if (activity == null) {
            throw new RuntimeException("秒杀活动不存在");
        }
        
        // 2. 校验活动时间
        LocalDateTime now = LocalDateTime.now();
        if (now.isBefore(activity.getStartTime())) {
            throw new RuntimeException("秒杀尚未开始");
        }
        if (now.isAfter(activity.getEndTime())) {
            throw new RuntimeException("秒杀已结束");
        }
        
        // 3. Redis预扣减库存（幂等性保护）
        String stockKey = SECKILL_STOCK_KEY + activityId;
        Long remainingStock = redisUtil.decrement(stockKey, 1);
        
        if (remainingStock == null || remainingStock < 0) {
            redisUtil.increment(stockKey, 1);
            throw new RuntimeException("库存不足，秒杀失败");
        }
        
        // 4. Redis防重复购买（幂等性核心：setIfAbsent）
        String userKey = SECKILL_USER_KEY + userId + ":" + activityId;
        Boolean isFirstPurchase = redisUtil.setIfAbsent(userKey, "1", 3600, java.util.concurrent.TimeUnit.SECONDS);
        
        if (!isFirstPurchase) {
            redisUtil.increment(stockKey, 1);
            throw new RuntimeException("您已经参与过该秒杀活动");
        }
        
        // 5. 创建订单
        String orderNo = generateOrderNo();
        SeckillOrder order = new SeckillOrder();
        order.setUserId(userId);
        order.setActivityId(activityId);
        order.setOrderNo(orderNo);
        
        seckillOrderMapper.insert(order);
        
        // 6. 发送异步消息
        sendAsyncSeckillMessage(userId, activityId, orderNo, activity.getSeckillPrice());
        
        long endTime = System.currentTimeMillis();
        log.info("✅ [异步秒杀] 关键路径完成 | 用户ID: {} | 订单号: {} | 耗时: {}ms", 
                userId, orderNo, endTime - startTime);
        
        return orderNo;
    }
    
    /**
     * 发送异步秒杀消息（带幂等性ID）
     */
    private void sendAsyncSeckillMessage(Long userId, Long activityId, String orderNo, Integer price) {
        Map<String, Object> message = new HashMap<>();
        message.put("userId", userId);
        message.put("activityId", activityId);
        message.put("orderNo", orderNo);
        message.put("price", price);
        
        // 使用订单号作为幂等性ID
        String messageId = orderNo;
        SeckillMessageLog messageLog = new SeckillMessageLog();
        messageLog.setMessageId(messageId);
        messageLog.setMessageContent(message.toString());
        messageLog.setStatus(0);
        
        try {
            seckillMessageLogMapper.insert(messageLog);
            messageProducer.sendSeckillMessage(message);
            seckillMessageLogMapper.updateStatus(messageId, 1);
            log.info("📤 [异步秒杀] 消息发送成功 | 订单号: {}", orderNo);
        } catch (Exception e) {
            log.error("❌ [异步秒杀] 消息发送失败 | 订单号: {}", orderNo, e);
            seckillMessageLogMapper.setErrorMessage(messageId, e.getMessage());
            throw new RuntimeException("秒杀消息发送失败");
        }
    }
    
    private String generateOrderNo() {
        return "SK" + System.currentTimeMillis();
    }
}
