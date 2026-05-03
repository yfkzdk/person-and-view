"""
LLM 配置模型
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class ModelType(Enum):
    """模型类型"""
    CLAUDE = "claude"
    QWEN_LOCAL = "qwen_local"


class LLMConfig(BaseModel):
    """LLM 配置"""
    model_type: ModelType = ModelType.CLAUDE
    model_name: str = "claude-sonnet-4-6"
    max_tokens: int = Field(500, ge=1, le=4096, description="最大生成 token 数")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Top-p 采样")
    stream: bool = Field(True, description="是否流式生成")

    # API 配置
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    def to_claude_params(self) -> dict:
        """转换为 Claude API 参数"""
        return {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """聊天消息"""
    role: MessageRole
    content: str

    def to_claude_format(self) -> dict:
        """转换为 Claude API 格式"""
        return {
            "role": self.role.value,
            "content": self.content
        }
