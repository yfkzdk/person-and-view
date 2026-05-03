"""
提示词模板测试
"""
import pytest
from src.llm.prompt_templates import PromptTemplates
from src.models.llm_config import ChatMessage, MessageRole


def test_create_system_prompt_narrator():
    """测试创建叙事者系统提示词"""
    prompt = PromptTemplates.create_system_prompt(persona="narrator")

    assert "语音叙事助手" in prompt
    assert "导演指令" in prompt


def test_create_system_prompt_assistant():
    """测试创建助手系统提示词"""
    prompt = PromptTemplates.create_system_prompt(persona="assistant")

    assert "智能语音助手" in prompt


def test_create_conversation_context():
    """测试创建对话上下文"""
    messages = [
        ChatMessage(role=MessageRole.USER, content=f"消息{i}")
        for i in range(15)
    ]

    context = PromptTemplates.create_conversation_context(messages, max_messages=10)

    # 应该只保留最近10条
    assert len(context) == 10
    assert context[0].content == "消息5"
    assert context[-1].content == "消息14"


def test_format_user_input_with_context():
    """测试带上下文的用户输入格式化"""
    formatted = PromptTemplates.format_user_input(
        user_input="你好",
        context="用户正在探索森林"
    )

    assert "[上下文: 用户正在探索森林]" in formatted
    assert "你好" in formatted


def test_format_user_input_without_context():
    """测试不带上下文的用户输入格式化"""
    formatted = PromptTemplates.format_user_input(user_input="你好")

    assert formatted == "你好"


def test_create_narrative_prompt():
    """测试创建叙事提示词"""
    prompt = PromptTemplates.create_narrative_prompt(
        scene="黑暗的森林",
        user_action="向前走"
    )

    assert "场景：黑暗的森林" in prompt
    assert "用户行为：向前走" in prompt
    assert "描述接下来发生的事情" in prompt
