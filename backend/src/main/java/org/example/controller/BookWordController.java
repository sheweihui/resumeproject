package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.entity.UserBookWord;
import org.example.service.UserBookWordService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 单词书-单词关联控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/book-word")
public class BookWordController {
    
    @Autowired
    private UserBookWordService userBookWordService;
    /**
     * 从单词书移除单词
     */
    @DeleteMapping("/remove")
    public Result removeWordFromBook(@RequestParam Long userId, 
                                     @RequestParam Long bookId, 
                                     @RequestParam Long wordId) {
        try {
            userBookWordService.removeWordFromBook(userId, bookId, wordId);
            return Result.success("移除成功");
        } catch (Exception e) {
            log.error("移除单词失败", e);
            return Result.error("移除失败: " + e.getMessage());
        }
    }

    /**
     * 查询单词书中的单词列表
     */
    @GetMapping("/list")
    public Result getWordsByBook(@RequestParam Long userId, 
                                 @RequestParam Long bookId) {
        try {
            List<UserBookWord> words = userBookWordService.getWordsByBook(userId, bookId);
            return Result.success(words);
        } catch (Exception e) {
            log.error("查询单词列表失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }

    /**
     * 标记单词为已掌握
     */
    @PutMapping("/master")
    public Result markAsMastered(@RequestParam Long userId, 
                                 @RequestParam Long bookId, 
                                 @RequestParam Long wordId) {
        try {
            userBookWordService.markAsMastered(userId, bookId, wordId);
            return Result.success("标记成功");
        } catch (Exception e) {
            log.error("标记失败", e);
            return Result.error("标记失败: " + e.getMessage());
        }
    }

    /**
     * 添加笔记
     */
    @PutMapping("/note")
    public Result addNote(@RequestParam Long userId, 
                         @RequestParam Long bookId, 
                         @RequestParam Long wordId,
                         @RequestParam String note) {
        try {
            userBookWordService.addNote(userId, bookId, wordId, note);
            return Result.success("添加笔记成功");
        } catch (Exception e) {
            log.error("添加笔记失败", e);
            return Result.error("添加笔记失败: " + e.getMessage());
        }
    }

    /**
     * 更新复习次数
     */
    @PutMapping("/review")
    public Result updateReviewCount(@RequestParam Long userId, 
                                    @RequestParam Long bookId, 
                                    @RequestParam Long wordId) {
        try {
            userBookWordService.updateReviewCount(userId, bookId, wordId);
            return Result.success("更新成功");
        } catch (Exception e) {
            log.error("更新复习次数失败", e);
            return Result.error("更新失败: " + e.getMessage());
        }
    }

    /**
     * 查询未掌握的单词
     */
    @GetMapping("/unmastered")
    public Result getUnmasteredWords(@RequestParam Long userId, 
                                     @RequestParam Long bookId) {
        try {
            List<UserBookWord> words = userBookWordService.getUnmasteredWords(userId, bookId);
            return Result.success(words);
        } catch (Exception e) {
            log.error("查询未掌握单词失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }

    /**
     * 查询已掌握的单词
     */
    @GetMapping("/mastered")
    public Result getMasteredWords(@RequestParam Long userId, 
                                   @RequestParam Long bookId) {
        try {
            List<UserBookWord> words = userBookWordService.getMasteredWords(userId, bookId);
            return Result.success(words);
        } catch (Exception e) {
            log.error("查询已掌握单词失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
}
