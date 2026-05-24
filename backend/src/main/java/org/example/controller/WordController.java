package org.example.controller;

import lombok.extern.slf4j.Slf4j;
import org.example.common.Result;
import org.example.context.UserContextHolder;
import org.example.dto.DeleteInfo;
import org.example.entity.UserWord;
import org.example.service.AiWordService;
import org.example.service.UserWordService;
import org.example.utils.RedisUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 单词控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/word")
public class WordController {
    
    @Autowired
    private UserWordService userWordService;
    @Autowired
    private AiWordService aiWordService;
    @Autowired
    private RedisUtil redisUtil;
    
    /**
     * 获取单词详情
     */
    @GetMapping("/{id}")
    public Result<UserWord> getWordDetail(@PathVariable Long id) {
        try {
            UserWord word = userWordService.getById(id);
            if (word != null) {
                return Result.success(word);
            }
            return Result.error("单词不存在");
        } catch (Exception e) {
            log.error("查询单词详情失败", e);
            return Result.error("查询失败: " + e.getMessage());
        }
    }
    
    /**
     * 添加单词
     */
    @PostMapping
    public Result addWord(@RequestBody UserWord userWord) {
        try {
            userWordService.save(userWord);
            return Result.success("添加成功");
        } catch (Exception e) {
            log.error("添加单词失败", e);
            return Result.error("添加失败: " + e.getMessage());
        }
    }

    /**
     * 删除单词
     */
    @DeleteMapping("/remove/{id}")
    public Result deleteWord(@RequestBody DeleteInfo deleteInfo) {
        try {
            userWordService.deleteById(deleteInfo.getWordId());
            String user = "user:"+String.valueOf(UserContextHolder.getUserId())+"word:"+String.valueOf(deleteInfo.getBookId())+"words";
            redisUtil.delete(user);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除单词失败", e);
            return Result.error("删除失败: " + e.getMessage());
        }
    }

    /**
     * 使用AI填充单词信息
     */
    @PostMapping("/ai-fill")
    public Result<UserWord> aiFillWord(@RequestBody String wordText) {
        try {
            log.debug("🤖 [AI填充] 开始处理单词: {}", wordText);
            UserWord word = aiWordService.enrichAndSaveUserWord(wordText);//ai填充单词信息
            log.debug("✅ [AI填充] 完成 | 单词: {}", word.getWordText());
            return Result.success(word);
        } catch (Exception e) {
            log.error("AI填充单词失败", e);
            return Result.error("填充失败: " + e.getMessage());
        }
    }
    /**
     * 更新单词信息
     */
    @PutMapping("/{id}")
    public Result updateWord(@PathVariable Long id, @RequestBody UserWord userWord) {
        try {
            userWord.setId(id);
            userWordService.update(userWord);
            return Result.success("更新成功");
        } catch (Exception e) {
            log.error("更新单词失败", e);
            return Result.error("更新失败: " + e.getMessage());
        }
    }
}
