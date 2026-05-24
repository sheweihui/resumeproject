package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.context.UserContextHolder;
import org.example.dto.StoreBookQueryDTO;
import org.example.dto.FlashSaleDTO;
import org.example.entity.PublicWord;
import org.example.entity.UserPointsAccount;
import org.example.service.UserCheckinService;
import org.example.service.UserPointsAccountService;
import org.example.service.StoreService;
import org.example.vo.CheckinVO;
import org.example.vo.PointsVO;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 商店控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/store")
public class StoreController {
    
    @Autowired
    private UserPointsAccountService userPointsAccountService;
    
    @Autowired
    private StoreService storeService;
    
    @Autowired
    private UserCheckinService userCheckinService;

    /**
     * 获取当前用户积分余额
     */
    @GetMapping("/points/balance")
    public Result<PointsVO> getPointsBalance() {
        try {
            Long userId = UserContextHolder.getUserId();
            UserPointsAccount account = userPointsAccountService.getAccountByUserId(userId);
            
            PointsVO vo = new PointsVO();
            BeanUtils.copyProperties(account, vo);
            
            log.debug("📊 [积分查询] 用户ID: {} | 余额: {}", userId, account.getBalance());
            
            return Result.success(vo);
        } catch (Exception e) {
            log.error("❌ [积分查询] 失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
    
    /**
     * 每日签到
     */
    @PostMapping("/checkin")
    public Result<CheckinVO> checkin() {
        try {
            Long userId = UserContextHolder.getUserId();
            CheckinVO result = userCheckinService.checkin(userId);
            
            if (!result.getCheckedIn()) {
                return Result.success("今日已签到", result);
            }
            
            String msg = String.format("签到成功！获得%d积分，连续签到%d天", 
                    result.getPointsEarned(), result.getContinuousDays());
            
            return Result.success(msg, result);
        } catch (Exception e) {
            log.error("❌ [签到] 失败", e);
            return Result.error("签到失败: " + e.getMessage());
        }
    }
    
    /**
     * 获取商店单词书列表
     */
    @GetMapping("/books")
    public Result queryStoreBooks(StoreBookQueryDTO queryDTO) {
        try {
            log.info("📚 [REQUEST] GET /api/store/books | 用户: {}", UserContextHolder.getUserId());
            return Result.success(storeService.queryStoreBooks(queryDTO));
        } catch (Exception e) {
            log.error("❌ [商店] 查询失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
    
    /**
     * 获取单词书详情
     */
    @GetMapping("/books/{id}")
    public Result getBookDetail(@PathVariable Long id) {
        try {
            log.debug("🔍 [商店] 查询单词书详情 | ID: {}", id);
            return Result.success(storeService.getBookDetail(id));
        } catch (Exception e) {
            log.error("❌ [商店] 查询详情失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
    
    /**
     * 购买单词书（原有方法）
     */
    @PostMapping("/books/{id}/purchase")
    public Result purchaseBook(@PathVariable Long id) {
        try {
            Long userId = UserContextHolder.getUserId();
            log.info("🛒 [购买] 用户ID: {} | 单词书ID: {}", userId, id);
            log.info("------------------------------------------------------");
            Long bookId = storeService.purchaseBook(userId, id);
            return Result.success("购买成功", bookId);
        } catch (Exception e) {
            log.error("❌ [购买] 失败", e);
            return Result.error("购买失败: " + e.getMessage());
        }
    }

    /**
     * 获取单词书包含的单词列表
     */
    @GetMapping("/books/{id}/words")
    public Result<List<PublicWord>> queryBookWords(@PathVariable Long id) {
        try {
            log.info("💾 [DB] 从数据库查询单词书的单词列表 | 单词书ID: {}", id);
            return Result.success(storeService.queryBookWords(id));
        } catch (Exception e) {
            log.error("❌ [DB] 查询单词失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
    /**
     * 获取秒杀商品列表
     */
    @GetMapping("/flash-sale/list")
    public Result<List<FlashSaleDTO>> queryFlashSaleList() {
        try {
            log.info("⚡ [秒杀] 查询秒杀列表");
            return Result.success(storeService.queryFlashSaleList());
        } catch (Exception e) {
            log.error("❌ [秒杀] 查询失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
    /**
     * 秒杀购买
     */
    @PostMapping("/flash-sale/purchase/{id}")
    public Result<Long> purchaseFlashSaleBook(@PathVariable Long id) {
        try {
            Long userId = UserContextHolder.getUserId();
            log.info("⚡ [秒杀] 秒杀购买 | 用户ID: {} | 秒杀ID: {}", userId, id);
            return Result.success("秒杀成功", storeService.flashsale(userId, id));
        } catch (Exception e) {
            log.error("❌ [秒杀] 秒杀失败", e);
            return Result.error("秒杀失败: " + e.getMessage());
        }
    }
}
