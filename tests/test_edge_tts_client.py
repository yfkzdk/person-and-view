"""
Edge TTS 客户端测试
"""
import pytest
import asyncio
from src.tts.edge_tts_client import EdgeTTSClient
from src.models.tts_config import TTSConfig, VoiceConfig


@pytest.mark.asyncio
async def test_edge_tts_client_creation():
    """测试 Edge TTS 客户端创建"""
    config = TTSConfig()
    client = EdgeTTSClient(config)

    assert client.config == config


@pytest.mark.asyncio
async def test_synthesize_text():
    """测试文本合成"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural"
        )
    )
    client = EdgeTTSClient(config)

    # 合成文本
    audio_chunks = []
    async for chunk in client.synthesize("你好世界"):
        audio_chunks.append(chunk)

    # 验证生成了音频数据
    assert len(audio_chunks) > 0
    assert all(len(chunk) > 0 for chunk in audio_chunks)


@pytest.mark.asyncio
async def test_synthesize_with_rate():
    """测试带语速的合成"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural",
            rate=1.5  # 1.5倍速
        )
    )
    client = EdgeTTSClient(config)

    audio_chunks = []
    async for chunk in client.synthesize("快速说话"):
        audio_chunks.append(chunk)

    assert len(audio_chunks) > 0


@pytest.mark.asyncio
async def test_list_voices():
    """测试列出音色"""
    voices = await EdgeTTSClient.list_voices("zh-CN")

    # 验证返回了音色列表
    assert len(voices) > 0
    assert all(v["Locale"].startswith("zh-CN") for v in voices)
