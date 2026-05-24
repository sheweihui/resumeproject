package org.example.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.example.entity.SeckillMessageLog;

/**
 * 秒杀消息日志Mapper接口
 */
@Mapper
public interface SeckillMessageLogMapper {
    
    int insert(SeckillMessageLog messageLog);
    
    SeckillMessageLog selectByMessageId(@Param("messageId") String messageId);
    
    int updateStatus(@Param("messageId") String messageId, @Param("status") Integer status);
    
    int incrementRetryCount(@Param("messageId") String messageId);
    
    int setErrorMessage(@Param("messageId") String messageId, @Param("errorMessage") String errorMessage);
}
