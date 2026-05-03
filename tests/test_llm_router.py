"""
LLM 路由器测试
"""
import pytest
import asyncio
import os
from src.llm.llm_router import LLMRouter
from src.models.llm_config import LLMConfig, ModelType
from src.llm.context_manager import ContextManager
from src.vad.interrupt_handler import InterruptHandler


def test_llm_router_creation():
    """测试 LLM 路由器创建"""
    config = LLMConfig()
    router = LLMRouter(config)

    assert router.config == config
    assert router.context_manager is not None


def test_llm_router_with_context():
    """测试带上下文的 LLM 路由器"""
    config = LLMConfig()
    context_manager = ContextManager(max_history=5)
    router = LLMRouter(config, context_manager=context_manager)

    assert router.context_manager.max_history == 5


def test_llm_router_with_interrupt():
    """测试带打断处理器的 LLM 路由器"""
    config = LLMConfig()
    interrupt_handler = InterruptHandler()
    router = LLMRouter(config, interrupt_handler=interrupt_handler)

    assert router.interrupt_handler is not None


def test_reset_context():
    """测试重置上下文"""
    config = LLMConfig()
    router = LLMRouter(config)

    # 添加一些消息
    router.context_manager.add_message(
        __import__("src.models.llm_config", fromlist=["MessageRole"]).MessageRole.USER,
        "你好"
    )

    # 重置
    router.reset_context()

    # 验证上下文已清空
    summary = router.get_context_summary()
    assert summary["total_messages"] == 0
    assert summary["has_system_prompt"] is True


def test_get_context_summary():
    """测试获取上下文摘要"""
    config = LLMConfig()
    router = LLMRouter(config)

    summary = router.get_context_summary()

    assert "total_messages" in summary
    assert "has_system_prompt" in summary


@pytest.mark.asyncio
async def test_chat_with_api():
    """测试带 API 的聊天"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = LLMConfig(api_key=api_key, max_tokens=50)
    router = LLMRouter(config)

    # 流式聊天
    text_chunks = []
    async for chunk in router.chat("你好"):
        text_chunks.append(chunk)

    assert len(text_chunks) > 0