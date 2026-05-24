package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.dto.UserDTO;
import org.example.entity.User;
import org.example.mq.producer.MessageProducer;
import org.example.mq.producer.UserMessageProducer;
import org.example.service.UserService;
import org.example.utils.RedisUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.example.utils.UserEnum.USER_TOKEN;

/**
 * 用户控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/user")
public class UserController {
    
    @Autowired
    private UserService userService;
    @Autowired
    private RedisUtil redisUtil;
    @Autowired
    private MessageProducer messageProducer;
    @Autowired
    private UserMessageProducer userMessageProducer;

    private static final long EXPIRE_TIME = 2;
    private static final TimeUnit TOKEN_TIME_UTIL = TimeUnit.HOURS;
    
    /**
     * 用户注册
     */
    @PostMapping("/register")
    public Result<User> register(@RequestBody UserDTO userDTO) {
        try {
            String username = userDTO.getUsername();
            String password = userDTO.getPassword();
            String nickname = userDTO.getNickname();
            User user = userService.register(username, password, nickname);
            log.info("✅ [用户注册] 成功 | 用户名: {} | ID: {}", username, user.getId());
            // 创建用户账户
            messageProducer.CreateUserAccount(user.getId());
            return Result.success("注册成功", user);
        } catch (Exception e) {
            log.debug("用户注册失败：{}", e.getMessage());
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 用户登录
     */
    @PostMapping("/login")
    public Result login(@RequestBody UserDTO userDTO) {
        try {
            log.info("🔐 [用户登录] 开始登录 | 用户名: {}", userDTO.getUsername());
            
            User user = userService.login(userDTO.getUsername(), userDTO.getPassword());
            if(user == null){
                log.warn("⚠️  [用户登录] 用户不存在 | 用户名: {}", userDTO.getUsername());
                return Result.error("用户不存在");
            }
            
            // 清除密码信息
            user.setPassword(null);
            String token = UUID.randomUUID().toString().replace("-", "");
            String redisKey = USER_TOKEN.getValue() + ":" + token;
            redisUtil.set(redisKey, user, EXPIRE_TIME, TOKEN_TIME_UTIL);
            
            log.info("✅ [用户登录] 登录成功 | 用户ID: {} | 用户名: {} | Token: {}", 
                    user.getId(), userDTO.getUsername(), token);
            
            // 发送异步消息，缓存用户相关数据到Redis
            userMessageProducer.sendUserLoginMessage(user.getId(), token);
            return Result.success("登录成功", token);
        } catch (Exception e) {
            log.error("❌ [用户登录] 登录失败 | 用户名: {} | 错误: {}", userDTO.getUsername(), e.getMessage(), e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 获取用户信息
     */
    @GetMapping("/{id}")
    public Result<User> getUserInfo(@PathVariable Long id) {
        User user = userService.getById(id);
        if (user != null) {
            user.setPassword(null);
            return Result.success(user);
        }
        return Result.error("用户不存在");
    }

    /**
     * 退出登录
     */
    @PostMapping("/logout")
    public Result logout(@RequestBody Map<String, String> request) {
        try {
            // 从请求体中获取token: {"token": "0eed27e4b2b6429f8536310a28756752"}
            String token = request.get("token");
            
            if (token == null || token.isEmpty()) {
                log.warn("⚠️  [用户退出] token为空");
                return Result.error("token不能为空");
            }
            
            log.info("🚪 [用户退出] 开始退出登录 | token: {}", token);
            
            // 删除Redis中的token
            String redisKey = USER_TOKEN.getValue() + ":" + token;
            
            // 无论token是否存在，都尝试删除
            redisUtil.delete(redisKey);
            
            // 同时清除ThreadLocal
            org.example.context.UserContextHolder.clear();
            
            log.info("✅ [用户退出] 成功 | token: {}", token);
            return Result.success("退出登录成功");
            
        } catch (Exception e) {
            log.error("❌ [用户退出] 失败", e);
            return Result.error("退出登录失败");
        }
    }
    /**
     * 验证token是否有效
     */
    @PostMapping("/validate")
    public Result<Boolean> validateToken(@RequestBody Map<String, String> request) {
        return Result.success(redisUtil.hasKey(USER_TOKEN.getValue() + ":" + request.get("token")));
    }
}
