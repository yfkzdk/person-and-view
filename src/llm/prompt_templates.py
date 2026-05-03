"""
提示词模板
"""
from typing import List, Optional
from src.models.llm_config import ChatMessage, MessageRole


class PromptTemplates:
    """提示词模板管理器"""

    @staticmethod
    def create_system_prompt(
        persona: str = "narrator",
        language: str = "zh-CN"
    ) -> str:
        """
        创建系统提示词

        Args:
            persona: 人设 (narrator, assistant, character)
            language: 语言

        Returns:
            系统提示词
        """
        if persona == "narrator":
            return """你是一个实时语音叙事助手，负责为用户提供沉浸式的语音体验。

你的职责：
1. 用生动、自然的语言描述场景和事件
2. 根据用户输入调整叙事风格和节奏
3. 使用导演指令控制语音输出（如：[加速]、[减速]、[情绪:开心]）
4. 保持简洁，避免冗长

导演指令示例：
- [加速] 快速说话
- [减速] 慢速说话
- [压低音量] 降低音量
- [情绪:开心] 开心的语气

请用中文回复，保持自然流畅。"""

        elif persona == "assistant":
            return """你是一个智能语音助手，帮助用户解决问题。

你的职责：
1. 准确理解用户意图
2. 提供简洁、有用的回答
3. 必要时使用导演指令控制语音
4. 保持友好和专业

请用中文回复。"""

        else:
            return "你是一个有帮助的AI助手。"

    @staticmethod
    def create_conversation_context(
        messages: List[ChatMessage],
        max_messages: int = 10
    ) -> List[ChatMessage]:
        """
        创建对话上下文

        Args:
            messages: 历史消息列表
            max_messages: 最大消息数

        Returns:
            截断后的消息列表
        """
        if len(messages) <= max_messages:
            return messages

        # 保留最近的消息
        return messages[-max_messages:]

    @staticmethod
    def format_user_input(
        user_input: str,
        context: Optional[str] = None
    ) -> str:
        """
        格式化用户输入

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            格式化后的输入
        """
        if context:
            return f"[上下文: {context}]\n\n{user_input}"
        return user_input

    @staticmethod
    def create_narrative_prompt(
        scene: str,
        user_action: Optional[str] = None
    ) -> str:
        """
        创建叙事提示词

        Args:
            scene: 场景描述
            user_action: 用户行为

        Returns:
            叙事提示词
        """
        prompt = f"场景：{scene}\n\n"

        if user_action:
            prompt += f"用户行为：{user_action}\n\n"

        prompt += "请用生动的语言描述接下来发生的事情。"

        return prompt
