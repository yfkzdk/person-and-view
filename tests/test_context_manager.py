"""
上下文管理器测试
"""
import pytest
from src.llm.context_manager import ContextManager
from src.models.llm_config import MessageRole


def test_context_manager_creation():
    """测试上下文管理器创建"""
    manager = ContextManager(max_history=10)

    assert manager.max_history == 10
    assert len(manager.conversation_history) == 0


def test_set_system_prompt():
    """测试设置系统提示词"""
    manager = ContextManager()
    manager.set_system_prompt("你是一个助手")

    assert manager.system_prompt == "你是一个助手"


def test_add_message():
    """测试添加消息"""
    manager = ContextManager()

    manager.add_message(MessageRole.USER, "你好")
    manager.add_message(MessageRole.ASSISTANT, "你好！")

    assert len(manager.conversation_history) == 2
    assert manager.conversation_history[0].role == MessageRole.USER
    assert manager.conversation_history[1].role == MessageRole.ASSISTANT


def test_max_history_limit():
    """测试历史消息限制"""
    manager = ContextManager(max_history=5)

    # 添加10条消息
    for i in range(10):
        manager.add_message(MessageRole.USER, f"消息{i}")

    # 应该只保留最近5条
    assert len(manager.conversation_history) == 5
    assert manager.conversation_history[0].content == "消息5"
    assert manager.conversation_history[-1].content == "消息9"


def test_get_context_for_claude():
    """测试获取 Claude 格式上下文"""
    manager = ContextManager()
    manager.set_system_prompt("你是一个助手")
    manager.add_message(MessageRole.USER, "你好")

    context = manager.get_context_for_claude()

    assert len(context) == 2
    assert context[0]["role"] == "system"
    assert context[1]["role"] == "user"


def test_clear_history():
    """测试清空历史"""
    manager = ContextManager()
    manager.add_message(MessageRole.USER, "你好")
    manager.clear_history()

    assert len(manager.conversation_history) == 0


def test_get_last_user_message():
    """测试获取最后一条用户消息"""
    manager = ContextManager()
    manager.add_message(MessageRole.USER, "消息1")
    manager.add_message(MessageRole.ASSISTANT, "回复1")
    manager.add_message(MessageRole.USER, "消息2")

    last_user_msg = manager.get_last_user_message()

    assert last_user_msg.content == "消息2"


def test_get_conversation_summary():
    """测试获取对话摘要"""
    manager = ContextManager()
    manager.set_system_prompt("你是一个助手")
    manager.add_message(MessageRole.USER, "你好")
    manager.add_message(MessageRole.ASSISTANT, "你好！")
    manager.add_message(MessageRole.USER, "再见")

    summary = manager.get_conversation_summary()

    assert summary["total_messages"] == 3
    assert summary["user_messages"] == 2
    assert summary["assistant_messages"] == 1
    assert summary["has_system_prompt"] is True
