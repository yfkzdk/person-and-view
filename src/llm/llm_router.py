"""
LLM 路由器
"""
from typing import AsyncIterator, Optional
import logging

from src.models.llm_config import LLMConfig, ModelType, ChatMessage, MessageRole
from src.llm.deepseek_client import DeepSeekClient
from src.llm.context_manager import ContextManager
from src.llm.prompt_templates import PromptTemplates
from src.vad.interrupt_handler import InterruptHandler
from src.config import settings
from src.models.person_profile import PersonProfile

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 路由器 - 根据配置选择模型"""

    def __init__(
        self,
        config: LLMConfig,
        context_manager: Optional[ContextManager] = None,
        interrupt_handler: Optional[InterruptHandler] = None
    ):
        """
        初始化 LLM 路由器

        Args:
            config: LLM 配置
            context_manager: 上下文管理器
            interrupt_handler: 打断处理器
        """
        self.config = config
        self.context_manager = context_manager or ContextManager()
        self.interrupt_handler = interrupt_handler

        # 设置默认系统提示词
        if not self.context_manager.system_prompt:
            self.context_manager.set_system_prompt(
                PromptTemplates.create_system_prompt(persona="narrator")
            )

        # 初始化客户端
        self._client = None

        # 人物档案
        self.person_profile: Optional[PersonProfile] = None

    def set_person_profile(self, profile: PersonProfile):
        """
        设置人物档案

        Args:
            profile: 人物档案
        """
        self.person_profile = profile
        # 更新系统提示词
        system_prompt = profile.to_system_prompt()
        self.context_manager.set_system_prompt(system_prompt)
        logger.info(f"Person profile set: {profile.name}")

    def clear_person_profile(self):
        """清除人物档案，恢复默认"""
        self.person_profile = None
        self.context_manager.set_system_prompt(
            PromptTemplates.create_system_prompt(persona="narrator")
        )
        logger.info("Person profile cleared")

    @property
    def client(self):
        """懒加载客户端"""
        if self._client is None:
            # 根据配置选择客户端
            provider = settings.LLM_PROVIDER.lower()

            if provider == "deepseek":
                # DeepSeek 客户端
                self._client = DeepSeekClient(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL,
                    model=settings.DEEPSEEK_MODEL,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE
                )
                logger.info("Using DeepSeek client")

            elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
                # Claude 客户端（延迟导入，anthropic包可选）
                from src.llm.claude_client import ClaudeClient
                self._client = ClaudeClient(
                    self.config,
                    self.interrupt_handler
                )
                logger.info("Using Claude client")

            else:
                raise ValueError(f"Unsupported LLM provider: {provider} or missing API key")
        return self._client

    async def chat(
        self,
        user_input: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        流式聊天 — context is transient (injected into current turn only, not persisted).
        """
        # Store RAW user input in history (context is NOT embedded to avoid
        # exponential pollution when past turns are re-sent to the API).
        self.context_manager.add_message(MessageRole.USER, user_input)

        # 流式生成
        full_response = []

        # 根据提供商选择不同的调用方式
        provider = settings.LLM_PROVIDER.lower()

        if provider == "deepseek":
            messages_for_api = []
            if self.context_manager.system_prompt:
                messages_for_api.append({"role": "system", "content": self.context_manager.system_prompt})

            history = self.context_manager.conversation_history
            for i, msg in enumerate(history):
                content = msg.content
                # Inject transient context ONLY into the LAST user message
                if context and msg.role == MessageRole.USER and i == len(history) - 1:
                    content = f"[上下文: {context}]\n\n{content}"
                messages_for_api.append({"role": msg.role.value, "content": content})

            async for chunk in self.client.chat_stream(
                messages_for_api,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                full_response.append(chunk)
                yield chunk

        else:
            # Claude with context injected into current user message
            raw_messages = self.context_manager.get_context_for_claude()
            if context and raw_messages:
                last_user_idx = -1
                for i in range(len(raw_messages) - 1, -1, -1):
                    if raw_messages[i].get("role") == "user":
                        last_user_idx = i
                        break
                if last_user_idx >= 0:
                    raw_messages[last_user_idx]["content"] = (
                        f"[上下文: {context}]\n\n{raw_messages[last_user_idx]['content']}"
                    )
            async for chunk in self.client.stream_generate(
                messages=raw_messages,
                system_prompt=self.context_manager.system_prompt
            ):
                full_response.append(chunk)
                yield chunk

        # 保存助手回复
        response_text = "".join(full_response)
        self.context_manager.add_message(MessageRole.ASSISTANT, response_text)

        logger.info(f"Chat completed: {len(response_text)} chars")

    async def chat_non_stream(
        self,
        user_input: str,
        context: Optional[str] = None
    ) -> str:
        """
        非流式聊天

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            生成的文本
        """
        # 格式化用户输入
        formatted_input = PromptTemplates.format_user_input(
            user_input, context
        )

        # 添加到上下文
        self.context_manager.add_message(MessageRole.USER, formatted_input)

        # 获取消息列表
        messages = self.context_manager.get_context_for_claude()

        # 非流式生成
        response = await self.client.generate(
            messages=messages,
            system_prompt=self.context_manager.system_prompt
        )

        # 保存助手回复
        self.context_manager.add_message(MessageRole.ASSISTANT, response)

        return response

    def reset_context(self):
        """重置对话上下文"""
        self.context_manager.clear_history()
        self.context_manager.set_system_prompt(
            PromptTemplates.create_system_prompt(persona="narrator")
        )
        logger.info("Context reset")

    def get_context_summary(self) -> dict:
        """获取上下文摘要"""
        return self.context_manager.get_conversation_summary()