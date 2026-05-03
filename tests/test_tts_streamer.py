"""
TTS 流式合成器测试（使用统一函数接口）
"""
import pytest
import asyncio
from src.tts.tts_streamer import get_tts_audio, get_tts_format
from src.config import settings


def test_get_tts_format():
    """测试获取TTS格式"""
    fmt = get_tts_format()
    assert fmt in ("mp3", "wav")


@pytest.mark.asyncio
@pytest.mark.skip(reason="需要网络，CI 中跳过")
async def test_stream_synthesis():
    """测试流式合成"""
    audio_chunks = []
    async for chunk in get_tts_audio("你好世界"):
        audio_chunks.append(chunk)
    assert len(audio_chunks) > 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="需要网络，CI 中跳过")
async def test_long_text_synthesis():
    """测试长文本合成"""
    audio_chunks = []
    async for chunk in get_tts_audio("这是测试文本。" * 5):
        audio_chunks.append(chunk)
    assert len(audio_chunks) > 0
