"""
TTS 流式合成器 - 统一接口
根据配置选择 Edge TTS 或 CosyVoice
"""
import os
import logging
import asyncio
from typing import AsyncIterator

from src.config import settings

logger = logging.getLogger(__name__)


def get_tts_format() -> str:
    """Return the audio format ('mp3' or 'wav') based on current TTS provider"""
    provider = settings.TTS_PROVIDER.lower()
    return "wav" if provider == "cosyvoice" else "mp3"


async def get_tts_audio(
    text: str,
    voice: str = None,
    rate: float = None,
    pitch: int = None,
    style: str = None
) -> AsyncIterator[bytes]:
    """
    统一TTS接口 - 根据配置选择TTS提供商

    Args:
        text: 要合成的文本
        voice: 可选的语音名称（EdgeTTS: 完整voice name; CosyVoice: profile name）
        rate: 语速 (-50% ~ +200%)
        pitch: 音调 (-50Hz ~ +50Hz)
        style: 说话风格（仅 Edge TTS 支持）

    Yields:
        音频数据块 (bytes)
    """
    provider = settings.TTS_PROVIDER.lower()

    if provider == "cosyvoice":
        async for chunk in _cosyvoice_synthesize(text, voice):
            yield chunk
    else:
        async for chunk in _edge_tts_synthesize(text, voice, rate, pitch, style):
            yield chunk


async def _edge_tts_synthesize(
    text: str,
    voice: str = None,
    rate: float = None,
    pitch: int = None,
    style: str = None
) -> AsyncIterator[bytes]:
    """Edge TTS 合成 - 支持完整的声音参数调优"""
    import edge_tts

    voice = voice or f"{settings.TTS_LANGUAGE}-{settings.TTS_VOICE}"

    # 构建 edge_tts.Communicate 参数（只传非空值）
    kwargs = {"voice": voice}

    actual_rate = rate if rate is not None else settings.TTS_RATE
    if actual_rate != 1.0:
        kwargs["rate"] = f"{actual_rate - 1.0:+.0%}"

    actual_pitch = pitch if pitch is not None else settings.TTS_PITCH
    if actual_pitch != 0:
        kwargs["pitch"] = f"{actual_pitch:+d}Hz"

    communicate = edge_tts.Communicate(text, **kwargs)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


async def _cosyvoice_synthesize(text: str, voice: str = None) -> AsyncIterator[bytes]:
    """CosyVoice 零样本克隆合成"""
    from src.tts.cosyvoice_client import CosyVoiceTTSClient

    voice_name = voice or settings.COSYVOICE_DEFAULT_VOICE

    # 初始化客户端（单例模式）
    if not hasattr(_cosyvoice_synthesize, '_client'):
        model_dir = settings.COSYVOICE_MODEL_DIR or None

        _cosyvoice_synthesize._client = CosyVoiceTTSClient(
            model_dir=model_dir,
            voice_name=voice_name,
        )
        _cosyvoice_synthesize._current_voice = voice_name

    client = _cosyvoice_synthesize._client

    # If voice changed, switch the client's voice profile
    if voice_name != _cosyvoice_synthesize._current_voice:
        client.switch_voice(voice_name)
        _cosyvoice_synthesize._current_voice = voice_name

    # 使用流式合成
    async for wav_chunk in client.synthesize_streaming(text):
        if wav_chunk:
            yield wav_chunk
            await asyncio.sleep(0)  # 让出控制权