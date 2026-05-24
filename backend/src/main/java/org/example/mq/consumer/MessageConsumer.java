package org.example.mq.consumer;

import com.rabbitmq.client.Channel;
import lombok.extern.slf4j.Slf4j;
import org.example.annotation.RabbitMqMessage;
import org.example.annotation.RabbitTime;
import org.example.config.RabbitMQConfig;
import org.example.context.UserContextHolder;
import org.example.entity.PublicBookWord;
import org.example.entity.PublicVocabularyBook;
import org.example.entity.User;
import org.example.entity.UserPointsAccount;
import org.example.entity.UserVocabularyBook;
import org.example.mapper.PublicBookWordMapper;
import org.example.mapper.PublicVocabularyBookMapper;
import org.example.service.UserBookWordService;
import org.example.service.UserPointsAccountService;
import org.example.service.UserService;
import org.example.service.UserVocabularyBookService;
import org.example.mapper.SeckillMessageLogMapper;
import org.example.entity.SeckillMessageLog;
import org.example.utils.RedisUtil;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.example.utils.UserEnum.USER_TOKEN;

/**
 * 消息消费者
 */
@Slf4j
@Component
public class MessageConsumer {
    
    private final Jackson2JsonMessageConverter messageConverter = new Jackson2JsonMessageConverter();

    @Autowired
    private RedisUtil redisUtil;
    @Autowired
    private UserService userService;
    @Autowired
    private UserVocabularyBookService userVocabularyBookService;
    @Autowired
    private UserPointsAccountService userPointsAccountService;
    @Autowired
    private UserBookWordService userBookWordService;
    @Autowired
    private PublicBookWordMapper publicBookWordMapper;
    @Autowired
    private PublicVocabularyBookMapper publicVocabularyBookMapper;
    @Autowired
    private SeckillMessageLogMapper seckillMessageLogMapper;
    /**
     * 消费用户注册消息
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_USER_REGISTER)
    public void consumeUserRegister(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        
        try {
            // 解析消息
            Map<String, Object> body = (Map<String, Object>) messageConverter.fromMessage(message);
            Long userId = ((Number) body.get("userId")).longValue();
            String username = (String) body.get("username");
            
            log.info("📥 [消费者] 处理用户注册消息 | 用户ID: {} | 用户名: {}", userId, username);
            
            // TODO: 在这里处理业务逻辑
            // 例如：发送欢迎邮件、初始化用户数据等
            
            // 手动确认消息
            channel.basicAck(deliveryTag, false);
            log.debug("✅ [消费者] 消息已确认 | 用户ID: {}", userId);
            
        } catch (Exception e) {
            log.error("❌ [消费者] 处理用户注册消息失败", e);
            // 拒绝消息并重新入队
            channel.basicNack(deliveryTag, false, true);
        }
    }
    
    /**
     * 消费用户登录消息（异步缓存用户信息到Redis）
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_USER_LOGIN)
    public void consumeUserLogin(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        
        try {
            Map<String, Object> body = (Map<String, Object>) messageConverter.fromMessage(message);
            
            Long userId = ((Number) body.get("userId")).longValue();
            String token = (String) body.get("token");
            log.info("📥 [消费者] 开始缓存用户信息 | 用户ID: {}", userId);
            
            // TODO: 在这里实现缓存逻辑
            // 1. 查询用户详细信息
            // 2. 查询用户的单词本列表
            // 3. 查询用户的学习进度
            // 4. 查询用户的积分余额
            // 5. 将所有数据缓存到Redis
            
            // 示例伪代码：
             User user = userService.getById(userId);
             List<UserVocabularyBook> books = userVocabularyBookService.listByUserId(userId);
             UserPointsAccount points = userPointsAccountService.getAccountByUserId(userId);
             //token:user:books:userId
             redisUtil.set("user:books:" + userId, books, 2, TimeUnit.HOURS);
             redisUtil.set("user:points:" + userId, points, 2, TimeUnit.HOURS);
            String redisKey = USER_TOKEN.getValue() + ":" + token;

            redisUtil.set(redisKey, user, 2, TimeUnit.HOURS);
            
            log.info("✅ [消费者] 用户信息缓存完成 | 用户ID: {}", userId);
            log.debug("💾 [缓存用户信息] 缓存完成 | 用户Token: {}", token);
            // 手动确认消息
            channel.basicAck(deliveryTag, false);
            
        } catch (Exception e) {
            log.error("❌ [消费者] 缓存用户信息失败", e);
            // 拒绝消息并重新入队
            channel.basicNack(deliveryTag, false, true);
        }
    }
    
    /**
     * 消费积分奖励消息
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_POINTS_REWARD)
    public void consumePointsReward(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        
        try {
            Map<String, Object> body = (Map<String, Object>) messageConverter.fromMessage(message);
            
            Long userId = ((Number) body.get("userId")).longValue();
            Integer points = ((Number) body.get("points")).intValue();
            String reason = (String) body.get("reason");
            
            log.info("📥 [消费者] 处理积分奖励消息 | 用户ID: {} | 积分: {} | 原因: {}", userId, points, reason);
            
            // TODO: 在这里处理积分增加逻辑
            // 例如：调用 PointsAccountService.addPoints()
            
            // 手动确认消息
            channel.basicAck(deliveryTag, false);
            log.debug("✅ [消费者] 消息已确认 | 用户ID: {}", userId);
            
        } catch (Exception e) {
            log.error("❌ [消费者] 处理积分奖励消息失败", e);
            // 拒绝消息并重新入队
            channel.basicNack(deliveryTag, false, true);
        }
    }
    
    /**
     * 消费通知消息
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_NOTIFICATION)
    public void consumeNotification(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        
        try {
            Map<String, Object> body = (Map<String, Object>) messageConverter.fromMessage(message);
            
            String type = (String) body.get("type");
            String content = (String) body.get("content");
            Long userId = ((Number) body.get("userId")).longValue();
            
            log.info("📥 [消费者] 处理通知消息 | 类型: {} | 用户ID: {} | 内容: {}", type, userId, content);
            
            // TODO: 在这里处理通知逻辑
            // 例如：发送邮件、短信、推送等
            
            // 手动确认消息
            channel.basicAck(deliveryTag, false);
            log.debug("✅ [消费者] 消息已确认 | 用户ID: {}", userId);
            
        } catch (Exception e) {
            log.error("❌ [消费者] 处理通知消息失败", e);
            // 拒绝消息并重新入队
            channel.basicNack(deliveryTag, false, true);
        }
    }
    
    /**
     * 消费购买消息（异步处理单词复制等非关键路径操作）
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_PURCHASE)
    public void consumePurchase(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        long startTime = System.currentTimeMillis();
        long stepStart;
        
        try {
            Map<String, Object> body = (Map<String, Object>) messageConverter.fromMessage(message);
            
            Long userId = ((Number) body.get("userId")).longValue();
            Long productId = ((Number) body.get("productId")).longValue();
            Long userBookId = ((Number) body.get("userBookId")).longValue();
            Long publicBookId = body.get("publicBookId") != null ? ((Number) body.get("publicBookId")).longValue() : null;
            Integer pricePaid = ((Number) body.get("pricePaid")).intValue();
            
            log.info("⏱️ [异步消费者-总] 开始处理购买消息 | 用户ID: {} | 商品ID: {} | 用户书ID: {}", 
                    userId, productId, userBookId);
            
            // 步骤1：复制单词关联（最耗时的操作）
            stepStart = System.currentTimeMillis();
            if (publicBookId != null) {
                // 查询公共单词书中的所有单词
                List<PublicBookWord> publicBookWords = publicBookWordMapper.selectByBookId(publicBookId);
                
                if (publicBookWords != null && !publicBookWords.isEmpty()) {
                    // 批量插入用户单词关联
                    int count = userBookWordService.batchAddWordsToBook(userId, userBookId, publicBookWords);
                    log.info("⏱️ [异步消费者-步骤1] 复制单词完成 | 数量: {} | 耗时: {}ms", count, System.currentTimeMillis() - stepStart);
                } else {
                    log.warn("⚠️ [异步消费者] 公共单词书没有单词 | 公共书ID: {}", publicBookId);
                }
            } else {
                log.warn("⚠️ [异步消费者] 未提供公共单词书ID");
            }
            
            // 步骤2：更新单词书的单词数量
            stepStart = System.currentTimeMillis();
            if (publicBookId != null) {
                PublicVocabularyBook publicBook = publicVocabularyBookMapper.selectById(publicBookId);
                if (publicBook != null) {
                    userVocabularyBookService.updateVocabularyBook(
                        userBookId, 
                        null, 
                        null, 
                        null, 
                        null
                    );
                    // TODO: 需要添加 updateWordCount 方法
                    log.info("⏱️ [异步消费者-步骤2] 更新单词书统计 | 耗时: {}ms", System.currentTimeMillis() - stepStart);
                }
            }
            
            // 步骤3：更新商品销售数量
            stepStart = System.currentTimeMillis();
            // TODO: 调用 StoreProductMapper.updateSalesCount
            log.info("⏱️ [异步消费者-步骤3] 更新销售统计 | 耗时: {}ms", System.currentTimeMillis() - stepStart);
            
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            log.info("✅ [异步消费者-总计] 购买消息处理完成 | 用户ID: {} | 总耗时: {}ms", userId, duration);
            
            // 手动确认消息
            channel.basicAck(deliveryTag, false);
            
        } catch (Exception e) {
            log.error("❌ [异步消费者] 处理购买消息失败 | 错误: {}", e.getMessage(), e);
            // 拒绝消息并重新入队
            channel.basicNack(deliveryTag, false, true);
        }
    }
    /**
     * 消费用户账户创建消息（异步初始化用户账户数据）
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_USER_ACCOUNT)
    @RabbitMqMessage(message = "来源:/api/user/register")
    @RabbitTime(message = "用户账户创建消息处理耗时")
    public void consumeUserAccount(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
            
        try {
            // 直接获取用户ID（生产者发送的是Long类型）
            Long userId = (Long) messageConverter.fromMessage(message);
                
            log.info("📥 [消费者] 开始处理用户账户初始化 | 用户ID: {}", userId);
            userPointsAccountService.createAccount(userId);
            log.info("📤 [消费者] 用户账户初始化完成 | 用户ID: {}", userId);
            
            // ✅ 成功时确认消息
            channel.basicAck(deliveryTag, false);
                
        } catch (Exception e) {
            log.error("❌ [消费者] 处理用户账户初始化失败 | 错误: {}", e.getMessage(), e);
            
            // 获取重试次数
            Integer retryCount = (Integer) message.getMessageProperties().getHeaders().get("x-retry-count");
            if (retryCount == null) {
                retryCount = 0;
            }
            
            // 最大重试次数
            final int MAX_RETRY = 3;
            
            if (retryCount < MAX_RETRY) {
                // 增加重试次数
                retryCount++;
                message.getMessageProperties().getHeaders().put("x-retry-count", retryCount);
                
                log.warn("⚠️ [消费者] 第 {} 次重试 | 用户ID: {}", retryCount, UserContextHolder.getUserId());
                
                // 重新入队
                channel.basicNack(deliveryTag, false, true);
            } else {
                log.error("❌ [消费者] 达到最大重试次数({})，丢弃消息 | 用户ID: {}", MAX_RETRY,  UserContextHolder.getUserId());
                
                // ❌ 拒绝消息，不再重新入队（进入死信队列或丢弃）
                channel.basicNack(deliveryTag, false, false);
                
                // TODO: 发送告警通知人工处理
            }
        }
    }
    
    /**
     * 消费秒杀消息（异步处理秒杀订单的后续操作）
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_SECKILL)
    public void consumeSeckill(Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        
        try {
            Map<String, Object> body = (Map<String, Object>) messageConverter.fromMessage(message);
            
            Long userId = ((Number) body.get("userId")).longValue();
            Long activityId = ((Number) body.get("activityId")).longValue();
            String orderNo = (String) body.get("orderNo");
            Integer price = ((Number) body.get("price")).intValue();
            
            // 幂等性检查：通过订单号（messageId）查询是否已处理
            SeckillMessageLog messageLog = seckillMessageLogMapper.selectByMessageId(orderNo);
            if (messageLog != null && messageLog.getStatus() == 1) {
                log.info("✅ [异步消费者-秒杀] 消息已处理，跳过 | 订单号: {}", orderNo);
                channel.basicAck(deliveryTag, false);
                return;
            }
            
            log.info("⏱️ [异步消费者-秒杀] 开始处理 | 用户ID: {} | 活动ID: {} | 订单号: {}", 
                    userId, activityId, orderNo);
            
            // 步骤1：扣除积分（传入订单号作为幂等性标识）
            userPointsAccountService.deductPoints(
                userId,
                price,
                6,
                "秒杀商品",
                activityId,
                orderNo
            );
            
            // 更新消息状态为成功（幂等性标记）
            seckillMessageLogMapper.updateStatus(orderNo, 1);
            
            log.info("✅ [异步消费者-秒杀] 处理完成 | 用户ID: {} | 订单号: {}", userId, orderNo);
            
            // ✅ 手动确认消息
            channel.basicAck(deliveryTag, false);
            
        } catch (Exception e) {
            log.error("❌ [异步消费者-秒杀] 处理失败 | 错误: {}", e.getMessage(), e);
            
            // 获取重试次数
            Integer retryCount = (Integer) message.getMessageProperties().getHeaders().get("x-retry-count");
            if (retryCount == null) {
                retryCount = 0;
            }
            
            final int MAX_RETRY = 3;
            
            if (retryCount < MAX_RETRY) {
                retryCount++;
                message.getMessageProperties().getHeaders().put("x-retry-count", retryCount);
                
                log.warn("⚠️ [异步消费者-秒杀] 第 {} 次重试 | 订单号: {}", retryCount, 
                        message.getMessageProperties().getHeaders().get("orderNo"));
                
                channel.basicNack(deliveryTag, false, true);
            } else {
                log.error("❌ [异步消费者-秒杀] 达到最大重试次数({})，丢弃消息 | 订单号: {}", 
                        MAX_RETRY, message.getMessageProperties().getHeaders().get("orderNo"));
                
                channel.basicNack(deliveryTag, false, false);
            }
        }
    }
}
