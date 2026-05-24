package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 数据库错误日志测试控制器
 * 用于验证 MySQL 执行失败的日志是否正常输出
 */
@Slf4j
@RestController
@RequestMapping("/api/test/db-error")
public class DatabaseErrorTestController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private UserMapper userMapper;

    /**
     * 测试1：SQL语法错误
     */
    @GetMapping("/syntax-error")
    public Result testSyntaxError() {
        log.info("🧪 [测试] 触发 SQL 语法错误");
        try {
            // 故意写错 SQL 语法
            jdbcTemplate.execute("SELECT * FROM non_existent_table WHERE invalid syntax");
            return Result.success("测试完成");
        } catch (Exception e) {
            log.error("❌ [测试] SQL语法错误已捕获 | 错误: {}", e.getMessage(), e);
            return Result.error("SQL语法错误: " + e.getMessage());
        }
    }

    /**
     * 测试2：表不存在错误
     */
    @GetMapping("/table-not-exist")
    public Result testTableNotExist() {
        log.info("🧪 [测试] 触发表不存在错误");
        try {
            jdbcTemplate.queryForList("SELECT * FROM this_table_does_not_exist");
            return Result.success("测试完成");
        } catch (Exception e) {
            log.error("❌ [测试] 表不存在错误已捕获 | 错误: {}", e.getMessage(), e);
            return Result.error("表不存在: " + e.getMessage());
        }
    }

    /**
     * 测试3：字段不存在错误
     */
    @GetMapping("/column-not-exist")
    public Result testColumnNotExist() {
        log.info("🧪 [测试] 触发字段不存在错误");
        try {
            jdbcTemplate.queryForList("SELECT non_existent_column FROM user LIMIT 1");
            return Result.success("测试完成");
        } catch (Exception e) {
            log.error("❌ [测试] 字段不存在错误已捕获 | 错误: {}", e.getMessage(), e);
            return Result.error("字段不存在: " + e.getMessage());
        }
    }

    /**
     * 测试4：唯一约束冲突（需要先有数据）
     */
    @GetMapping("/duplicate-key")
    public Result testDuplicateKey() {
        log.info("🧪 [测试] 触发唯一约束冲突");
        try {
            // 尝试插入重复的用户名（假设 username 有唯一约束）
            jdbcTemplate.update(
                "INSERT INTO user (username, password, nickname) VALUES ('test_duplicate_user', '123456', '测试用户')"
            );
            // 第二次插入，应该失败
            jdbcTemplate.update(
                "INSERT INTO user (username, password, nickname) VALUES ('test_duplicate_user', '123456', '测试用户2')"
            );
            return Result.success("测试完成");
        } catch (Exception e) {
            log.error("❌ [测试] 唯一约束冲突已捕获 | 错误: {}", e.getMessage(), e);
            return Result.error("唯一约束冲突: " + e.getMessage());
        }
    }

    /**
     * 测试5：外键约束失败
     */
    @GetMapping("/foreign-key-error")
    public Result testForeignKeyError() {
        log.info("🧪 [测试] 触发外键约束失败");
        try {
            // 尝试插入一个不存在的外键引用
            jdbcTemplate.update(
                "INSERT INTO user_vocabulary_book (user_id, book_name) VALUES (999999999, '测试书籍')"
            );
            return Result.success("测试完成");
        } catch (Exception e) {
            log.error("❌ [测试] 外键约束失败已捕获 | 错误: {}", e.getMessage(), e);
            return Result.error("外键约束失败: " + e.getMessage());
        }
    }

    /**
     * 测试6：空指针异常导致的数据库错误
     */
    @GetMapping("/null-pointer")
    public Result testNullPointerException() {
        log.info("🧪 [测试] 触发空指针异常");
        try {
            Long nullId = null;
            userMapper.selectById(nullId);
            return Result.success("测试完成");
        } catch (Exception e) {
            log.error("❌ [测试] 空指针异常已捕获 | 错误: {}", e.getMessage(), e);
            return Result.error("空指针异常: " + e.getMessage());
        }
    }
}
