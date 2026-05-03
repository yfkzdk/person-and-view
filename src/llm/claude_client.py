"""
Claude API 客户端
"""
from typing import AsyncIterator, List, Optional
import logging
import os

from src.models.llm_config import LLMConfig, MessageRole
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude API 客户端"""

    def __init__(
        self,
        config: LLMConfig,
        interrupt_handler: Optional[InterruptHandler] = None
    ):
        """
        初始化 Claude 客户端

        Args:
            config: LLM 配置
            interrupt_handler: 打断处理器
        """
        import anthropic
        self._anthropic = anthropic

        self.config = config
        self.interrupt_handler = interrupt_handler

        # 初始化客户端
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in config or environment")

        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        logger.info(f"Claude client initialized with model: {config.model_name}")

    async def stream_generate(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        流式生成文本

        Args:
            messages: 消息列表
            system_prompt: 系统提示词

        Yields:
            文本块
        """
        try:
            # 准备参数
            params = self.config.to_claude_params()
            params["messages"] = messages

            if system_prompt:
                params["system"] = system_prompt

            logger.info(f"Starting stream generation with {len(messages)} messages")

            # 流式生成
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    # 检查打断
                    if self.interrupt_handler:
                        await self.interrupt_handler.check_and_raise()

                    yield text

        except VADInterruptException:
            logger.info("LLM generation interrupted by user")
            raise

        except self._anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

    async def generate(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        非流式生成文本

        Args:
            messages: 消息列表
            system_prompt: 系统提示词

        Returns:
            生成的文本
        """
        try:
            params = self.config.to_claude_params()
            params["messages"] = messages
            params["stream"] = False

            if system_prompt:
                params["system"] = system_prompt

            logger.info(f"Starting generation with {len(messages)} messages")

            response = await self.client.messages.create(**params)

            # 提取文本内容
            text = "".join(
                block.text
                for block in response.content
                if hasattr(block, "text")
            )

            logger.info(f"Generated {len(text)} characters")
            return text

        except self._anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def count_tokens(self, messages: List[dict]) -> int:
        """
        计算 token 数量

        Args:
            messages: 消息列表

        Returns:
            token 数量
        """
        try:
            response = await self.client.messages.count_tokens(
                model=self.config.model_name,
                messages=messages
            )
            return response.input_tokens

        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            return 0
