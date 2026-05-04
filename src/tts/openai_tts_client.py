"""
OpenAI TTS client — cloud-based, no local inference.

Uses httpx REST API calls. Supports:
- tts-1 / tts-1-hd / gpt-4o-mini-tts models
- All standard voices: alloy, echo, fable, onyx, nova, shimmer
- Speed control (0.25 — 4.0)
"""
import os
import logging
import httpx
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# OpenAI TTS voices mapped by role
VOICE_MAP = {
    "man": "onyx",       # deep male
    "woman": "nova",     # warm female
    "girl": "shimmer",   # young female
    "boy": "echo",       # young male
    "neutral_male": "fable",    # balanced male
    "neutral_female": "alloy",  # balanced female
}

# Default voice profiles for common character types
CHARACTER_VOICE = {
    "tong_jincheng": {"voice": "fable", "speed": 1.05, "desc": "自信直率的男声"},
    "therapist": {"voice": "nova", "speed": 0.9, "desc": "温暖柔和的女声"},
    "friend": {"voice": "alloy", "speed": 1.0, "desc": "自然随意的中性声"},
    "mentor": {"voice": "onyx", "speed": 0.88, "desc": "沉稳权威的男声"},
    "storyteller": {"voice": "shimmer", "speed": 0.95, "desc": "清澈的女声"},
    "companion": {"voice": "echo", "speed": 1.0, "desc": "温暖年轻的男声"},
}


def get_openai_voice(profile_name: str) -> dict:
    """Get OpenAI voice settings for a profile name."""
    return CHARACTER_VOICE.get(profile_name, {"voice": "alloy", "speed": 1.0})


async def openai_tts_synthesize(
    text: str,
    api_key: str = None,
    model: str = "tts-1",
    voice: str = "alloy",
    speed: float = 1.0,
    response_format: str = "mp3",
) -> AsyncIterator[bytes]:
    """Stream-synthesize text via OpenAI TTS API.

    Args:
        text: Text to synthesize (max 4096 chars for tts-1)
        api_key: OpenAI API key
        model: tts-1, tts-1-hd, or gpt-4o-mini-tts
        voice: alloy, echo, fable, onyx, nova, shimmer
        speed: 0.25 to 4.0
        response_format: mp3, opus, aac, flac, wav, pcm

    Yields:
        Audio chunks as bytes
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return

    url = "https://api.openai.com/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "voice": voice,
        "input": text[:4096],  # tts-1 limit
        "speed": max(0.25, min(4.0, speed)),
        "response_format": response_format,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"OpenAI TTS error {response.status_code}: {error_body.decode()[:200]}")
                    return

                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk

        except httpx.TimeoutException:
            logger.error("OpenAI TTS request timed out")
        except Exception as e:
            logger.error(f"OpenAI TTS failed: {e}")
