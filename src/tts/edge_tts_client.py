"""
Edge TTS 客户端
"""
import edge_tts
import asyncio
from typing import AsyncIterator
from src.models.tts_config import TTSConfig
import logging

logger = logging.getLogger(__name__)


class EdgeTTSClient:
    """Edge TTS 客户端"""

    def __init__(self, config: TTSConfig):
        """
        初始化 Edge TTS 客户端

        Args:
            config: TTS 配置
        """
        self.config = config

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """
        流式合成文本

        Args:
            text: 要合成的文本

        Yields:
            音频数据块 (bytes)
        """
        # 获取 Edge TTS 参数
        params = self.config.to_edge_tts_params()

        logger.info(f"Synthesizing text: {text[:50]}...")
        logger.debug(f"TTS params: {params}")

        try:
            # 创建 Communicate 对象
            communicate = edge_tts.Communicate(
                text,
                **params
            )

            # 流式生成音频
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    async def synthesize_to_file(self, text: str, output_path: str):
        """
        合成文本到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
        """
        params = self.config.to_edge_tts_params()

        communicate = edge_tts.Communicate(text, **params)
        await communicate.save(output_path)

        logger.info(f"Audio saved to {output_path}")

    @staticmethod
    async def list_voices(language: str = "zh-CN"):
        """
        列出可用音色

        Args:
            language: 语言代码

        Returns:
            音色列表
        """
        voices = await edge_tts.list_voices()

        # 过滤指定语言
        filtered_voices = [
            v for v in voices
            if v["Locale"].startswith(language)
        ]

        return filtered_voices
