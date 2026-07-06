# WordFlash AI Agent

`ai-agent` 是 WordFlash 的大模型应用服务，用 FastAPI 独立部署，通过 HTTP 与 Java 后端解耦。

## 目标

- 将大模型能力从 Java 主服务中拆出，避免模型调用阻塞核心业务。
- 演示 RAG 检索增强、Function Calling / Tool Calling 和服务降级策略。
- 将积分查询、签到、单词本查询等 Java 后端接口抽象为模型可调用工具。

## 启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `BACKEND_BASE_URL` | Java 后端地址 | `http://localhost:8080` |
| `DEEPSEEK_BASE_URL` | OpenAI 兼容模型 API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_API_KEY` | 模型 API Key | 空 |
| `MODEL_NAME` | 模型名称 | `deepseek-chat` |
| `MODEL_TIMEOUT` | 模型调用超时时间 | `12` |

没有配置 `DEEPSEEK_API_KEY` 时，服务会自动使用 fallback 模式，不影响接口可用性。

## 接口

### 健康检查

```http
GET /health
```

### AI 对话

```http
POST /chat
Content-Type: application/json

{
  "user_id": 1,
  "message": "帮我看一下积分，并推荐今天要复习的单词",
  "token": "可选后端 token"
}
```

响应示例：

```json
{
  "answer": "我已经根据当前可用的后端数据帮你查询了相关信息。你可以继续问我积分、单词本或学习计划相关问题。",
  "mode": "fallback",
  "tools": [
    {
      "tool": "get_points",
      "success": false,
      "data": null,
      "error": "backend unavailable",
      "latency_ms": 12
    }
  ],
  "latency_ms": 45
}
```

## 工具调用设计

| 工具名 | 触发意图 | 后端接口 |
| --- | --- | --- |
| `get_points` | 查询积分、余额 | `/api/store/points/balance` |
| `checkin` | 签到、打卡 | `/api/store/checkin` |
| `list_books` | 查询单词本、单词书 | `/api/store/books` |

## 降级策略

- 模型 Key 未配置：直接使用规则化 fallback 回答。
- 模型超时：返回本地检索结果或友好提示。
- 后端工具调用失败：不影响整体对话，返回可解释错误。
- 上下文不足：提示用户补充更具体的问题。

## 简历可写点

- 基于 FastAPI 封装独立 AI Agent 服务，与 Java 后端通过 HTTP 解耦。
- 设计 RAG 检索增强流程，将本地业务知识和用户问题组合成 Prompt。
- 设计 Function Calling 工具调用框架，将积分查询、签到、单词本查询等后端接口抽象为工具。
- 实现模型不可用、后端工具失败时的降级策略，保证主流程可用性。
