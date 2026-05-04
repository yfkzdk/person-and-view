"""
TTS streamer — unified interface with multiple providers.

Providers:
- edge_tts: Microsoft Edge TTS (free, cloud), now with SSML for natural prosody
- edge_tts_ssml: Edge TTS with SSML prosody (natural pauses, emphasis, rate variation)
- openai: OpenAI TTS (paid, cloud), most natural synthetic voice
- cosyvoice: Zero-shot voice cloning (needs local GPU/model)
"""
import os
import logging
import asyncio
from typing import AsyncIterator, Optional

from src.config import settings

logger = logging.getLogger(__name__)


def get_tts_format() -> str:
    """Return audio format based on current TTS provider."""
    provider = settings.TTS_PROVIDER.lower()
    return "wav" if provider == "cosyvoice" else "mp3"


async def get_tts_audio(
    text: str,
    voice: str = None,
    rate: float = None,
    pitch: int = None,
    style: str = None,
    emotion: str = "neutral",
) -> AsyncIterator[bytes]:
    """Unified TTS interface.

    Args:
        text: Text to synthesize
        voice: Voice name (EdgeTTS: full name; OpenAI: voice ID; CosyVoice: profile)
        rate: Speaking rate (EdgeTTS: -50%~+200%; OpenAI: 0.25~4.0)
        pitch: Pitch shift in Hz (EdgeTTS only)
        style: Speaking style (EdgeTTS only)
        emotion: Emotion label for prosody tuning (edge_tts_ssml + openai)
    """
    provider = settings.TTS_PROVIDER.lower()

    if provider == "openai":
        async for chunk in _openai_tts_synthesize(text, voice, rate, emotion):
            yield chunk
    elif provider == "volcengine":
        async for chunk in _volcengine_tts_synthesize(text, voice, rate, emotion):
            yield chunk
    elif provider == "cosyvoice":
        async for chunk in _cosyvoice_synthesize(text, voice):
            yield chunk
    elif provider == "edge_tts_ssml":
        async for chunk in _edge_tts_ssml_synthesize(text, voice, rate, pitch, emotion):
            yield chunk
    else:  # edge_tts (default, raw — no SSML)
        async for chunk in _edge_tts_synthesize(text, voice, rate, pitch):
            yield chunk


async def _edge_tts_synthesize(
    text: str,
    voice: str = None,
    rate: float = None,
    pitch: int = None,
) -> AsyncIterator[bytes]:
    """Edge TTS — plain text mode (no SSML)."""
    import edge_tts

    voice = voice or f"{settings.TTS_LANGUAGE}-{settings.TTS_VOICE}"

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


async def _edge_tts_ssml_synthesize(
    text: str,
    voice: str = None,
    rate: float = None,
    pitch: int = None,
    emotion: str = "neutral",
) -> AsyncIterator[bytes]:
    """Edge TTS with SSML prosody for natural-sounding speech."""
    import edge_tts
    from src.tts.ssml_builder import build_ssml

    voice = voice or f"{settings.TTS_LANGUAGE}-{settings.TTS_VOICE}"

    # Build SSML with emotion-driven prosody
    ssml = build_ssml(
        text,
        voice=voice,
        emotion=emotion,
        rate_override=rate,
        pitch_override=pitch,
    )

    communicate = edge_tts.Communicate(ssml)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


async def _openai_tts_synthesize(
    text: str,
    voice: str = None,
    speed: float = None,
    emotion: str = "neutral",
) -> AsyncIterator[bytes]:
    """OpenAI TTS — cloud-based, most natural synthetic voice."""
    from src.tts.openai_tts_client import openai_tts_synthesize, get_openai_voice

    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_TTS_MODEL
    voice_setting = get_openai_voice(voice or "friend")
    voice_name = voice_setting["voice"]
    tts_speed = speed if speed is not None else voice_setting.get("speed", 1.0)

    # Adjust speed slightly based on emotion
    emotion_speed_mod = {"happy": 0.03, "sad": -0.05, "angry": 0.05, "calm": -0.08}
    tts_speed += emotion_speed_mod.get(emotion, 0)
    tts_speed = max(0.25, min(4.0, tts_speed))

    async for chunk in openai_tts_synthesize(
        text=text,
        api_key=api_key,
        model=model,
        voice=voice_name,
        speed=tts_speed,
    ):
        yield chunk
        await asyncio.sleep(0)  # yield control


async def _volcengine_tts_synthesize(
    text: str,
    voice: str = None,
    speed: float = None,
    emotion: str = "neutral",
) -> AsyncIterator[bytes]:
    """火山引擎 TTS — 国内访问，中自然语音，免费额度 10万字符/月."""
    from src.tts.volcengine_tts_client import volcengine_tts_synthesize, get_volc_voice

    voice_setting = get_volc_voice(voice or "friend")
    voice_type = voice_setting["speaker"]
    tts_speed = speed if speed is not None else voice_setting.get("speed", 1.0)
    tts_volume = voice_setting.get("volume", 1.0)

    async for chunk in volcengine_tts_synthesize(
        text=text,
        appid=settings.VOLCENGINE_APP_ID,
        token=settings.VOLCENGINE_ACCESS_TOKEN,
        voice_type=voice_type,
        speed=tts_speed,
        volume=tts_volume,
        emotion=emotion,
    ):
        yield chunk
        await asyncio.sleep(0)


async def create_streaming_synthesizer(
    voice: str = None,
    speed: float = None,
):
    """Create a StreamingVolcengineSynthesizer for sentence-level streaming TTS.

    Returns an initialized synthesizer ready to accept sentences via feed_sentence().
    Caller must call synth.finish() then synth.flush() to get audio, then await synth._cleanup().
    """
    from src.tts.volcengine_tts_client import StreamingVolcengineSynthesizer, get_volc_voice

    voice_setting = get_volc_voice(voice or "friend")
    speaker = voice_setting["speaker"]
    tts_speed = speed if speed is not None else voice_setting.get("speed", 1.0)
    tts_volume = voice_setting.get("volume", 1.0)

    synth = StreamingVolcengineSynthesizer(
        appid=settings.VOLCENGINE_APP_ID,
        token=settings.VOLCENGINE_ACCESS_TOKEN,
        speaker=speaker,
        speed=tts_speed,
        volume=tts_volume,
    )
    await synth._connect()
    return synth


async def _cosyvoice_synthesize(text: str, voice: str = None) -> AsyncIterator[bytes]:
    """CosyVoice zero-shot cloning synthesis."""
    from src.tts.cosyvoice_client import CosyVoiceTTSClient

    voice_name = voice or settings.COSYVOICE_DEFAULT_VOICE

    if not hasattr(_cosyvoice_synthesize, '_client'):
        model_dir = settings.COSYVOICE_MODEL_DIR or None
        _cosyvoice_synthesize._client = CosyVoiceTTSClient(
            model_dir=model_dir,
            voice_name=voice_name,
        )
        _cosyvoice_synthesize._current_voice = voice_name

    client = _cosyvoice_synthesize._client

    if voice_name != _cosyvoice_synthesize._current_voice:
        client.switch_voice(voice_name)
        _cosyvoice_synthesize._current_voice = voice_name

    async for wav_chunk in client.synthesize_streaming(text):
        if wav_chunk:
            yield wav_chunk
            await asyncio.sleep(0)
