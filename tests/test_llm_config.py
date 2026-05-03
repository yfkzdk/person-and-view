"""
LLM 配置测试
"""
import pytest
from src.models.llm_config import LLMConfig, ModelType, MessageRole, ChatMessage


def test_llm_config_creation():
    """测试 LLM 配置创建"""
    config = LLMConfig(
        model_type=ModelType.CLAUDE,
        model_name="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0.8
    )

    assert config.model_type == ModelType.CLAUDE
    assert config.model_name == "claude-sonnet-4-6"
    assert config.max_tokens == 500
    assert config.temperature == 0.8


def test_llm_config_default_values():
    """测试默认值"""
    config = LLMConfig()

    assert config.model_type == ModelType.CLAUDE
    assert config.max_tokens == 500
    assert config.temperature == 0.7


def test_model_type_enum():
    """测试模型类型枚举"""
    assert ModelType.CLAUDE.value == "claude"
    assert ModelType.QWEN_LOCAL.value == "qwen_local"


def test_to_claude_params():
    """测试转换为 Claude 参数"""
    config = LLMConfig(
        model_name="claude-sonnet-4-6",
        max_tokens=1000,
        temperature=0.9
    )

    params = config.to_claude_params()

    assert params["model"] == "claude-sonnet-4-6"
    assert params["max_tokens"] == 1000
    assert params["temperature"] == 0.9


def test_chat_message():
    """测试聊天消息"""
    message = ChatMessage(
        role=MessageRole.USER,
        content="你好"
    )

    assert message.role == MessageRole.USER
    assert message.content == "你好"

    claude_format = message.to_claude_format()
    assert claude_format["role"] == "user"
    assert claude_format["content"] == "你好"


def test_message_role_enum():
    """测试消息角色枚举"""
    assert MessageRole.SYSTEM.value == "system"
    assert MessageRole.USER.value == "user"
    assert MessageRole.ASSISTANT.value == "assistant"
