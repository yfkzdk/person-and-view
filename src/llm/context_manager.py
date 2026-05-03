"""
上下文管理器
"""
from typing import List, Optional
from src.models.llm_config import ChatMessage, MessageRole
from src.llm.prompt_templates import PromptTemplates
import logging

logger = logging.getLogger(__name__)


class ContextManager:
    """对话上下文管理器"""

    def __init__(self, max_history: int = 30):
        """
        初始化上下文管理器

        Args:
            max_history: 最大历史消息数
        """
        self.max_history = max_history
        self.conversation_history: List[ChatMessage] = []
        self.system_prompt: Optional[str] = None

    def set_system_prompt(self, prompt: str):
        """
        设置系统提示词

        Args:
            prompt: 系统提示词
        """
        self.system_prompt = prompt
        logger.info("System prompt updated")

    def add_message(self, role: MessageRole, content: str):
        """
        添加消息到历史

        Args:
            role: 消息角色
            content: 消息内容
        """
        message = ChatMessage(role=role, content=content)
        self.conversation_history.append(message)

        # 限制历史长度
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        logger.debug(f"Added {role.value} message: {content[:50]}...")

    def get_context_for_claude(self) -> List[dict]:
        """
        获取 Claude API 格式的上下文

        Returns:
            Claude API 消息列表
        """
        messages = []

        # 添加系统提示词
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # 添加对话历史
        for msg in self.conversation_history:
            messages.append(msg.to_claude_format())

        return messages

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_last_user_message(self) -> Optional[ChatMessage]:
        """
        获取最后一条用户消息

        Returns:
            最后一条用户消息，如果没有则返回 None
        """
        for msg in reversed(self.conversation_history):
            if msg.role == MessageRole.USER:
                return msg
        return None

    def get_conversation_summary(self) -> dict:
        """
        获取对话摘要

        Returns:
            对话摘要信息
        """
        user_messages = sum(1 for msg in self.conversation_history if msg.role == MessageRole.USER)
        assistant_messages = sum(1 for msg in self.conversation_history if msg.role == MessageRole.ASSISTANT)

        return {
            "total_messages": len(self.conversation_history),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "has_system_prompt": self.system_prompt is not None
        }
