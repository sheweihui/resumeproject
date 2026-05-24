package org.example.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.example.entity.SeckillOrder;

/**
 * 秒杀订单Mapper接口
 */
@Mapper
public interface SeckillOrderMapper {
    
    /**
     * 插入秒杀订单
     */
    int insert(SeckillOrder order);
    
    /**
     * 根据用户ID和活动ID查询订单（防止重复购买）
     */
    SeckillOrder selectByUserAndActivity(@Param("userId") Long userId, @Param("activityId") Long activityId);
}
