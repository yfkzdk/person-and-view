"""
SSML builder for natural-sounding speech.

Converts plain text + emotion context into SSML with:
- Sentence-level pauses (mimics natural breathing)
- Rate variation (faster for excitement, slower for sadness)
- Pitch contour (higher for questions, lower for statements)
- Emphasis on key words

No local inference — pure text transformation before sending to cloud TTS.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Emotion → prosody mapping
EMOTION_PROFILE = {
    "happy": {"rate": 1.08, "pitch": "+5Hz", "pause_ms": 250, "style": "cheerful"},
    "sad": {"rate": 0.88, "pitch": "-4Hz", "pause_ms": 500, "style": "sad"},
    "angry": {"rate": 1.1, "pitch": "+8Hz", "pause_ms": 200, "style": "angry"},
    "fearful": {"rate": 1.02, "pitch": "+2Hz", "pause_ms": 350, "style": "fearful"},
    "surprised": {"rate": 1.06, "pitch": "+6Hz", "pause_ms": 280, "style": "cheerful"},
    "disgusted": {"rate": 0.92, "pitch": "-2Hz", "pause_ms": 320, "style": "serious"},
    "neutral": {"rate": 0.98, "pitch": "+0Hz", "pause_ms": 350, "style": "friendly"},
    "calm": {"rate": 0.9, "pitch": "-2Hz", "pause_ms": 400, "style": "calm"},
    "serious": {"rate": 0.93, "pitch": "-3Hz", "pause_ms": 380, "style": "serious"},
}

# Words/phrases that often deserve emphasis
EMPHASIS_PATTERNS = [
    (r"(不是|不对|错了|千万别|一定|必须|绝对)", "strong"),
    (r"(说实话|其实|但是|关键|重要的是|记住)", "moderate"),
    (r"(！|！!)$", "strong"),  # exclamation marks
    (r"(？|\?)$", "moderate"),  # questions get emphasis
]


def build_ssml(
    text: str,
    voice: str,
    emotion: str = "neutral",
    rate_override: float = None,
    pitch_override: int = None,
) -> str:
    """Build SSML-wrapped text with natural prosody.

    Args:
        text: Plain text to speak
        voice: Edge TTS voice name (e.g. 'zh-CN-YunyangNeural')
        emotion: Emotion label for prosody tuning
        rate_override: Override speaking rate
        pitch_override: Override pitch shift in Hz

    Returns:
        SSML string ready for Edge TTS
    """
    profile = EMOTION_PROFILE.get(emotion, EMOTION_PROFILE["neutral"])
    rate = rate_override if rate_override is not None else profile["rate"]
    pitch = f"{pitch_override:+d}Hz" if pitch_override is not None else profile["pitch"]
    pause_ms = profile["pause_ms"]

    # Split into sentences for pause insertion
    sentences = _split_sentences(text)

    ssml_parts = []
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue

        # Add inter-sentence pause (skip first sentence)
        if i > 0 and ssml_parts:
            ssml_parts.append(f'<break time="{pause_ms}ms"/>')

        # Apply emphasis detection to the sentence
        enhanced = _apply_emphasis(sentence)

        # Wrap sentence in prosody
        ssml_parts.append(
            f'<prosody rate="{rate:.2f}" pitch="{pitch}">{enhanced}</prosody>'
        )

    body = "\n        ".join(ssml_parts)

    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
    <voice name="{voice}">
        {body}
    </voice>
</speak>"""

    logger.debug(f"SSML ({emotion}, rate={rate:.2f}, pitch={pitch}): {text[:60]}...")
    return ssml


def build_ssml_simple(text: str, voice: str) -> str:
    """Minimal SSML with just sentence breaks — safe fallback."""
    return build_ssml(text, voice, emotion="neutral")


def _split_sentences(text: str) -> list[str]:
    """Split Chinese text into natural speech segments.

    Splits on Chinese punctuation but keeps short segments together
    so the speech doesn't sound choppy.
    """
    # Split on sentence-ending punctuation, keeping the delimiter
    parts = re.split(r"(?<=[。！？\.\!\?\n])", text)

    result = []
    buffer = ""
    for part in parts:
        combined = buffer + part
        if len(combined) < 6 and not re.search(r"[。！？\.\!\?\n]$", part):
            buffer = combined  # keep buffering short segments
        else:
            if combined.strip():
                result.append(combined.strip())
            buffer = ""

    if buffer.strip():
        # append buffer to last item
        if result:
            result[-1] += buffer.strip()
        else:
            result.append(buffer.strip())

    return result if result else [text]


def _apply_emphasis(sentence: str) -> str:
    """Wrap key words in emphasis tags for more natural intonation."""
    result = sentence
    for pattern, level in EMPHASIS_PATTERNS:
        result = re.sub(
            pattern,
            lambda m, lvl=level: f'<emphasis level="{lvl}">{m.group(0)}</emphasis>',
            result,
        )
    return result
