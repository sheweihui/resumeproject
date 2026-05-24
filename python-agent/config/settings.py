"""应用配置"""

import os
from dotenv import load_dotenv

load_dotenv()

# 后端 API 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))

# Agent 服务配置
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
AGENT_NAME = os.getenv("AGENT_NAME", "背单词助手")
AGENT_VERSION = "0.2.0"

# LLM 配置 (DeepSeek, 兼容 OpenAI SDK)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "data/agent.log")

# 数据存储
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
