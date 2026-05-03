"""
Claude API 客户端测试
"""
import pytest
import asyncio
from src.llm.claude_client import ClaudeClient
from src.models.llm_config import LLMConfig
from src.vad.interrupt_handler import InterruptHandler
import os


@pytest.mark.asyncio
async def test_claude_client_creation():
    """测试 Claude 客户端创建"""
    # 需要 API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = LLMConfig(api_key=api_key)
    client = ClaudeClient(config)

    assert client.config == config


@pytest.mark.asyncio
async def test_stream_generate():
    """测试流式生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = LLMConfig(
        api_key=api_key,
        model_name="claude-sonnet-4-6",
        max_tokens=100
    )
    client = ClaudeClient(config)

    messages = [
        {"role": "user", "content": "你好"}
    ]

    # 流式生成
    text_chunks = []
    async for chunk in client.stream_generate(messages):
        text_chunks.append(chunk)

    # 验证生成了文本
    assert len(text_chunks) > 0
    full_text = "".join(text_chunks)
    assert len(full_text) > 0


@pytest.mark.asyncio
async def test_generate():
    """测试非流式生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = LLMConfig(
        api_key=api_key,
        model_name="claude-sonnet-4-6",
        max_tokens=100
    )
    client = ClaudeClient(config)

    messages = [
        {"role": "user", "content": "你好"}
    ]

    # 非流式生成
    text = await client.generate(messages)

    assert len(text) > 0


@pytest.mark.asyncio
async def test_stream_with_interrupt():
    """测试带打断的流式生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = LLMConfig(api_key=api_key)
    interrupt_handler = InterruptHandler()
    client = ClaudeClient(config, interrupt_handler)

    # 触发打断
    interrupt_handler.trigger_interrupt()

    messages = [
        {"role": "user", "content": "你好"}
    ]

    # 尝试生成
    text_chunks = []
    with pytest.raises(Exception):  # 应该抛出打断异常
        async for chunk in client.stream_generate(messages):
            text_chunks.append(chunk)


@pytest.mark.asyncio
async def test_count_tokens():
    """测试 token 计数"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = LLMConfig(api_key=api_key)
    client = ClaudeClient(config)

    messages = [
        {"role": "user", "content": "你好"}
    ]

    token_count = await client.count_tokens(messages)

    # token 数量应该大于 0
    assert token_count > 0
