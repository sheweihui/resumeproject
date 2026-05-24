package org.example.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * RabbitMQ配置类
 * 
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                        RabbitMQ 消息路由对照表                               ║
 * ╠══════════════════════╦═════════════════════╦════════════════════╦═══════════╣
 * ║   生产者方法          ║   路由键             ║   队列              ║ 消费者   ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendUserRegister     ║ user.register       ║ queue.user.        ║ consume   ║
 * ║ Message()            ║                     ║ register           ║ UserReg.. ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendUserLogin        ║ user.login          ║ queue.user.login   ║ consume   ║
 * ║ (MessageProducer)    ║                     ║                    ║ UserLogin ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendUserLogin        ║ user.message        ║ USER_MESSAGE_QUEUE ║ consume   ║
 * ║ (UserMessageProducer)║                     ║                    ║ (UserMsg) ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendPointsReward     ║ points.reward       ║ queue.points.      ║ consume   ║
 * ║ Message()            ║                     ║ reward             ║ PointsRwd ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendNotification     ║ notification.{type} ║ queue.notification ║ consume   ║
 * ║ Message()            ║                     ║                    ║ Notificat ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendPurchase         ║ purchase.async      ║ queue.purchase     ║ consume   ║
 * ║ Message()            ║                     ║                    ║ Purchase  ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ CreateUserAccount()  ║ user.account.create ║ queue.user.account ║ consume   ║
 * ║                      ║                     ║                    ║ UserAccnt ║
 * ╠══════════════════════╬═════════════════════╬════════════════════╬═══════════╣
 * ║ sendSeckill          ║ seckill.order       ║ queue.seckill      ║ consume   ║
 * ║ Message()            ║                     ║                    ║ Seckill   ║
 * ╚══════════════════════╩═════════════════════╩════════════════════╩═══════════╝
 */
@Slf4j
@Configuration
public class RabbitMQConfig {
    
    // ==================== 交换机名称常量 ====================
    /**
     * 直连交换机 - 用于精确匹配路由键的消息
     */
    public static final String EXCHANGE_DIRECT = "exchange.direct";
    
    /**
     * 主题交换机 - 支持通配符匹配的消息
     */
    public static final String EXCHANGE_TOPIC = "exchange.topic";
    
    /**
     * 用户消息直连交换机
     */
    public static final String USER_MESSAGE_EXCHANGE = "USER_MESSAGE_EXCHANGE";

    // ==================== 队列名称常量 ====================
    /**
     * 用户注册队列
     */
    public static final String QUEUE_USER_REGISTER = "queue.user.register";
    
    /**
     * 用户登录队列（用于异步缓存用户信息）
     */
    public static final String QUEUE_USER_LOGIN = "queue.user.login";
    
    /**
     * 积分奖励队列
     */
    public static final String QUEUE_POINTS_REWARD = "queue.points.reward";
    
    /**
     * 通知队列
     */
    public static final String QUEUE_NOTIFICATION = "queue.notification";
    
    /**
     * 购买队列（用于异步处理单词复制等操作）
     */
    public static final String QUEUE_PURCHASE = "queue.purchase";
    
    /**
     * 用户账户初始化队列
     */
    public static final String QUEUE_USER_ACCOUNT = "queue.user.account";
    
    /**
     * 秒杀队列
     */
    public static final String QUEUE_SECKILL = "queue.seckill";
    
    /**
     * 用户消息队列（用于异步缓存用户相关数据）
     */
    public static final String USER_MESSAGE_QUEUE = "USER_MESSAGE_QUEUE";

    // ==================== 路由键常量 ====================
    /**
     * 用户注册路由键
     */
    public static final String ROUTING_KEY_USER_REGISTER = "user.register";
    
    /**
     * 用户登录路由键
     */
    public static final String ROUTING_KEY_USER_LOGIN = "user.login";
    
    /**
     * 积分奖励路由键
     */
    public static final String ROUTING_KEY_POINTS_REWARD = "points.reward";
    
    /**
     * 通知路由键（支持通配符）
     */
    public static final String ROUTING_KEY_NOTIFICATION = "notification.#";
    
    /**
     * 购买路由键
     */
    public static final String ROUTING_KEY_PURCHASE = "purchase.async";
    
    /**
     * 用户账户初始化路由键
     */
    public static final String ROUTING_KEY_USER_ACCOUNT = "user.account.create";
    
    /**
     * 秒杀路由键
     */
    public static final String ROUTING_KEY_SECKILL = "seckill.order";
    
    /**
     * 用户消息路由键
     */
    public static final String USER_MESSAGE_ROUTING_KEY = "user.message";

    // ==================== 消息转换器配置 ====================
    /**
     * JSON消息转换器
     */
    @Bean
    public Jackson2JsonMessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }
    
    /**
     * 配置RabbitTemplate
     */
    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.setMessageConverter(messageConverter());
        
        // 开启mandatory模式（确保消息路由失败时返回）
        rabbitTemplate.setMandatory(true);
        
        // 设置发布确认回调
        rabbitTemplate.setConfirmCallback((correlationData, ack, cause) -> {
            if (ack) {
                log.debug("✅ [RabbitMQ] 消息发送成功");
            } else {
                log.error("❌ [RabbitMQ] 消息发送失败: {}", cause);
            }
        });
        
        // 设置返回回调
        rabbitTemplate.setReturnsCallback(returned -> {
            log.error("❌ [RabbitMQ] 消息路由失败: {} | 路由键: {} | 交换机: {}", 
                    returned.getMessage(), 
                    returned.getRoutingKey(), 
                    returned.getExchange());
        });
        
        return rabbitTemplate;
    }

    // ==================== 交换机定义 ====================
    /**
     * 创建直连交换机
     */
    @Bean
    public DirectExchange directExchange() {
        return new DirectExchange(EXCHANGE_DIRECT, true, false);
    }
    
    /**
     * 创建主题交换机
     */
    @Bean
    public TopicExchange topicExchange() {
        return new TopicExchange(EXCHANGE_TOPIC, true, false);
    }
    
    /**
     * 创建用户消息直连交换机
     */
    @Bean
    public DirectExchange userMessageExchange() {
        return new DirectExchange(USER_MESSAGE_EXCHANGE, true, false);
    }

    // ==================== 队列定义 ====================
    /**
     * 创建用户注册队列
     */
    @Bean
    public Queue userRegisterQueue() {
        return QueueBuilder.durable(QUEUE_USER_REGISTER).build();
    }
    
    /**
     * 创建用户登录队列（用于异步缓存）
     */
    @Bean
    public Queue userLoginQueue() {
        return QueueBuilder.durable(QUEUE_USER_LOGIN).build();
    }
    
    /**
     * 创建积分奖励队列
     */
    @Bean
    public Queue pointsRewardQueue() {
        return QueueBuilder.durable(QUEUE_POINTS_REWARD).build();
    }
    
    /**
     * 创建通知队列
     */
    @Bean
    public Queue notificationQueue() {
        return QueueBuilder.durable(QUEUE_NOTIFICATION).build();
    }
    
    /**
     * 创建购买队列
     */
    @Bean
    public Queue purchaseQueue() {
        return QueueBuilder.durable(QUEUE_PURCHASE).build();
    }
    
    /**
     * 创建用户账户初始化队列
     */
    @Bean
    public Queue userAccountQueue() {
        return QueueBuilder.durable(QUEUE_USER_ACCOUNT).build();
    }
    
    /**
     * 创建秒杀队列
     */
    @Bean
    public Queue seckillQueue() {
        return QueueBuilder.durable(QUEUE_SECKILL).build();
    }
    
    /**
     * 创建用户消息队列
     */
    @Bean
    public Queue userMessageQueue() {
        return QueueBuilder.durable(USER_MESSAGE_QUEUE).build();
    }

    // ==================== 绑定关系配置 ====================
    
    // --- 直连交换机绑定 ---
    
    /**
     * 绑定用户注册队列到直连交换机
     * 路由: user.register → queue.user.register
     */
    @Bean
    public Binding userRegisterBinding(Queue userRegisterQueue, DirectExchange directExchange) {
        return BindingBuilder.bind(userRegisterQueue)
                .to(directExchange)
                .with(ROUTING_KEY_USER_REGISTER);
    }
    
    /**
     * 绑定用户登录队列到直连交换机
     * 路由: user.login → queue.user.login
     */
    @Bean
    public Binding userLoginBinding(Queue userLoginQueue, DirectExchange directExchange) {
        return BindingBuilder.bind(userLoginQueue)
                .to(directExchange)
                .with(ROUTING_KEY_USER_LOGIN);
    }
    
    /**
     * 绑定积分奖励队列到直连交换机
     * 路由: points.reward → queue.points.reward
     */
    @Bean
    public Binding pointsRewardBinding(Queue pointsRewardQueue, DirectExchange directExchange) {
        return BindingBuilder.bind(pointsRewardQueue)
                .to(directExchange)
                .with(ROUTING_KEY_POINTS_REWARD);
    }
    
    /**
     * 绑定购买队列到直连交换机
     * 路由: purchase.async → queue.purchase
     */
    @Bean
    public Binding purchaseBinding(Queue purchaseQueue, DirectExchange directExchange) {
        return BindingBuilder.bind(purchaseQueue)
                .to(directExchange)
                .with(ROUTING_KEY_PURCHASE);
    }
    
    /**
     * 绑定用户账户初始化队列到直连交换机
     * 路由: user.account.create → queue.user.account
     */
    @Bean
    public Binding userAccountBinding(Queue userAccountQueue, DirectExchange directExchange) {
        return BindingBuilder.bind(userAccountQueue)
                .to(directExchange)
                .with(ROUTING_KEY_USER_ACCOUNT);
    }
    
    /**
     * 绑定秒杀队列到直连交换机
     * 路由: seckill.order → queue.seckill
     */
    @Bean
    public Binding seckillBinding(Queue seckillQueue, DirectExchange directExchange) {
        return BindingBuilder.bind(seckillQueue)
                .to(directExchange)
                .with(ROUTING_KEY_SECKILL);
    }
    
    /**
     * 绑定用户消息队列到用户消息交换机
     * 路由: user.message → USER_MESSAGE_QUEUE
     */
    @Bean
    public Binding userMessageBinding(Queue userMessageQueue, DirectExchange userMessageExchange) {
        return BindingBuilder.bind(userMessageQueue)
                .to(userMessageExchange)
                .with(USER_MESSAGE_ROUTING_KEY);
    }
    
    // --- 主题交换机绑定 ---
    
    /**
     * 绑定通知队列到主题交换机
     * 路由: notification.# → queue.notification (支持通配符)
     */
    @Bean
    public Binding notificationBinding(Queue notificationQueue, TopicExchange topicExchange) {
        return BindingBuilder.bind(notificationQueue)
                .to(topicExchange)
                .with(ROUTING_KEY_NOTIFICATION);
    }
}
