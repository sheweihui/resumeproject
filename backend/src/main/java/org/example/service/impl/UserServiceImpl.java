package org.example.service.impl;

import cn.hutool.crypto.digest.BCrypt;
import org.example.entity.User;
import org.example.mapper.UserMapper;
import org.example.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * 用户服务实现类
 */
@Service
public class UserServiceImpl implements UserService {
    
    @Autowired
    private UserMapper userMapper;
    
    @Override
    public User register(String username, String password, String nickname) {
        // 检查用户名是否已存在
        User existUser = userMapper.selectByUsername(username);
        if (existUser != null) {
            throw new RuntimeException("用户名已存在");
        }
        
        // 创建新用户
        User user = new User();
        user.setUsername(username);
        user.setPassword(BCrypt.hashpw(password));
        user.setNickname(nickname != null ? nickname : username);
        userMapper.insert(user);
        return user;
    }
    
    @Override
    public User login(String username, String password) {
        // 查询用户
        User user = userMapper.selectByUsername(username);
        
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        // 验证密码
        if (!BCrypt.checkpw(password,user.getPassword())){
            throw new RuntimeException("密码错误");
        }
        
        return user;
    }
    
    @Override
    public User getById(Long id) {
        return userMapper.selectById(id);
    }
}
