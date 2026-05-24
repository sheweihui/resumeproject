package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.context.UserContextHolder;
import org.example.dto.CreateVocabularyBook;
import org.example.dto.DeleteInfo;
import org.example.dto.PutInfo;
import org.example.dto.WordDTO;
import org.example.entity.UserVocabularyBook;
import org.example.entity.UserWord;
import org.example.service.AiWordService;
import org.example.service.UserVocabularyBookService;
import org.example.service.UserWordService;
import org.example.utils.RedisUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 单词书控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/vocabulary-book")
public class VocabularyBookController {

    @Autowired
    private UserVocabularyBookService userVocabularyBookService;
    @Autowired
    private UserWordService userWordService;
    @Autowired
    private AiWordService aiWordService;
    @Autowired
    private RedisUtil redisUtil;

    /**
     * 创建单词书
     */
    @PostMapping
    public Result createVocabularyBook(@RequestBody CreateVocabularyBook createVocabularyBook) {
        try {
            createVocabularyBook.setCoverImage("");
            userVocabularyBookService.createVocabularyBook(
                    createVocabularyBook.getUserId(),
                    createVocabularyBook.getBookName(),
                    createVocabularyBook.getDescription(),
                    createVocabularyBook.getCoverImage()
            );
            return Result.success("创建成功");
        } catch (Exception e) {
            log.error("创建单词书失败", e);
            return Result.error("创建失败: " + e.getMessage());
        }
    }

    /**
     * 查询用户的所有单词书
     */
    @GetMapping({"/list/{userId}", "/vocab/list/{userId}"})
    public Result<List<UserVocabularyBook>> getBooksByUserId(@PathVariable Long userId) {
        try {
            userId = UserContextHolder.getUserId();
            log.debug("💾 [DB] 从数据库查询用户单词本列表 | 用户ID: {}", userId);
            List<UserVocabularyBook> books = userVocabularyBookService.getBooksByUserId(userId);
            log.debug("✅ [DB] 获取单词本列表成功 | 用户ID: {} | 数量: {}", userId, books != null ? books.size() : 0);
            return Result.success(books);
        } catch (Exception e) {
            log.error("❌ [DB] 查询单词书列表失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }

    /**
     * 查询单词书的单词详情
     */
    @GetMapping("/words")
    public Result<List<UserWord>> getBookByIdAllWord(@RequestParam("bookId") Long bookId) {
        try {
            if (bookId == null) {
                return Result.error("单词书ID不能为空");
            }

            String redisKey = "user:" + UserContextHolder.getUserId() + ":word:" + bookId + ":words";
            log.debug("🔍 [Redis] 尝试从 Redis 获取单词数据 | Key: {}", redisKey);
            List<UserWord> words = (List<UserWord>) redisUtil.get(redisKey);
            if (words != null) {
                redisUtil.expire(redisKey, 1, TimeUnit.DAYS);
                log.info("✅ [Redis] 缓存命中 | 单词数: {} | Key: {}", words.size(), redisKey);
                return Result.success(words);
            }

            log.info("💾 [DB] Redis 缓存未命中，从数据库查询 | 单词书ID: {}", bookId);
            List<UserWord> words1 = userVocabularyBookService.getBookByIdGetALLWORD(bookId);
            redisUtil.set(redisKey, words1, 1, TimeUnit.DAYS);
            log.info("✅ [DB→Redis] 从数据库获取并缓存到 Redis | 单词书ID: {} | 单词数: {} | Key: {}",
                    bookId, words1 != null ? words1.size() : 0, redisKey);
            return Result.success(words1);
        } catch (Exception e) {
            log.error("❌ 查询单词书单词列表失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }

    /**
     * 更新单词书
     */
    @PutMapping("/{id}")
    public Result updateVocabularyBook(@RequestBody PutInfo putInfo, @PathVariable Long id) {
        try {
            String bookName = putInfo.getBookName();
            String description = putInfo.getDescription();
            String coverImage = "";
            Integer isPublic = 0;
            userVocabularyBookService.updateVocabularyBook(id, bookName, description, coverImage, isPublic);
            Long userId = UserContextHolder.getUserId();
            redisUtil.delete(userId + ":books");
            return Result.success("更新成功");
        } catch (Exception e) {
            log.error("更新单词书失败", e);
            return Result.error("更新失败: " + e.getMessage());
        }
    }

    /**
     * 删除单词书
     */
    @DeleteMapping("/{id}")
    public Result deleteVocabularyBook(@PathVariable Long id) {
        try {
            userVocabularyBookService.deleteVocabularyBook(id);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除单词书失败", e);
            return Result.error("删除失败: " + e.getMessage());
        }
    }

    /**
     * 使用 AI 填充单词信息
     */
    @PostMapping("/word/ai-fill")
    public Result<UserWord> aiFillWord(@RequestBody String wordText) {
        try {
            log.debug("🤖 [AI填充] 开始处理单词: {}", wordText);
            UserWord word = aiWordService.enrichAndSaveUserWord(wordText);
            log.debug("✅ [AI填充] 完成 | 单词: {}", word.getWordText());
            return Result.success(word);
        } catch (Exception e) {
            log.error("AI填充单词失败", e);
            return Result.error("填充失败: " + e.getMessage());
        }
    }

    /**
     * 添加单词到单词书
     */
    @PostMapping("/add-word")
    public Result addWordToBook(@RequestBody WordDTO wordDTO) {
        try {
            log.debug("➕ [添加单词] 单词书ID: {} | 单词: {}", wordDTO.getBookId(), wordDTO.getWordText());
            userVocabularyBookService.addWordToBook(wordDTO);
            String redisKey = "user:" + UserContextHolder.getUserId() + ":word:" + wordDTO.getBookId() + ":words";
            redisUtil.delete(redisKey);
            log.debug("🗑️  [清除缓存] Key: {}", redisKey);
            return Result.success("添加成功");
        } catch (RuntimeException e) {
            log.warn("⚠️  [添加单词] 失败: {}", e.getMessage());
            return Result.error(e.getMessage());
        } catch (Exception e) {
            log.error("添加单词到单词书失败", e);
            return Result.error("添加失败: " + e.getMessage());
        }
    }

    /**
     * 从单词书删除单词
     */
    @DeleteMapping("/word/remove")
    public Result deleteWord(@RequestBody DeleteInfo deleteInfo) {
        try {
            userWordService.deleteById(deleteInfo.getWordId());
            String user = "user:" + UserContextHolder.getUserId() + "word:" + deleteInfo.getBookId() + "words";
            redisUtil.delete(user);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除单词失败", e);
            return Result.error("删除失败: " + e.getMessage());
        }
    }
}
