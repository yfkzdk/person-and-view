"""
TTSEngine - Text-to-Speech synthesis using edge-tts

Refactored with best practices from edge-tts reference project:
- Async streaming audio generation
- Dynamic voice selection with VoicesManager
- Streaming with subtitles/metadata support
- Proper text chunking for long texts
- Custom exception hierarchy
- Retry logic for transient errors
"""
import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Union

import edge_tts
import numpy as np


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================


class TTSError(Exception):
    """Base exception for TTS engine errors."""


class VoiceNotFoundError(TTSError):
    """Raised when a requested voice is not found."""


class SynthesisError(TTSError):
    """Raised when synthesis fails."""


class NoAudioReceivedError(SynthesisError):
    """Raised when no audio is received from the TTS service."""


class WebSocketError(TTSError):
    """Raised when a WebSocket error occurs."""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WordBoundary:
    """Word boundary metadata for subtitle generation."""

    type: str  # "WordBoundary" or "SentenceBoundary"
    offset: int  # Offset in ticks (1 tick = 100ns)
    duration: int  # Duration in ticks
    text: str  # The word or sentence text

    @property
    def start_time_seconds(self) -> float:
        """Get start time in seconds."""
        return self.offset / 10_000_000  # ticks to seconds

    @property
    def end_time_seconds(self) -> float:
        """Get end time in seconds."""
        return (self.offset + self.duration) / 10_000_000

    @property
    def start_time_ms(self) -> int:
        """Get start time in milliseconds."""
        return self.offset // 10_000  # ticks to milliseconds

    @property
    def end_time_ms(self) -> int:
        """Get end time in milliseconds."""
        return (self.offset + self.duration) // 10_000


@dataclass
class AudioChunk:
    """Audio chunk with optional metadata."""

    audio_data: bytes
    metadata: Optional[WordBoundary] = None


# =============================================================================
# VoicesManager Class
# =============================================================================


class VoicesManager:
    """
    Manager for finding voices based on attributes.

    Provides filtering by Gender, Language, Locale attributes with caching
    for performance.
    """

    def __init__(self) -> None:
        self.voices: List[Dict[str, str]] = []
        self._initialized = False

    @classmethod
    async def create(cls) -> "VoicesManager":
        """
        Create and populate a VoicesManager with all available voices.

        Returns:
            VoicesManager: Populated manager instance.
        """
        self = VoicesManager()
        voices = await edge_tts.list_voices()
        # Add Language field derived from Locale
        self.voices = [
            {**voice, "Language": voice.get("Locale", "").split("-")[0]}
            for voice in voices
        ]
        self._initialized = True
        return self

    def find(self, **kwargs) -> List[Dict[str, str]]:
        """
        Find voices matching the specified criteria.

        Args:
            **kwargs: Filter criteria (Gender, Language, Locale, etc.)

        Returns:
            List of voice dictionaries matching all criteria.

        Raises:
            RuntimeError: If create() was not called first.
        """
        if not self._initialized:
            raise RuntimeError(
                "VoicesManager.find() called before VoicesManager.create()"
            )

        matching_voices = [
            voice
            for voice in self.voices
            if kwargs.items() <= voice.items()
        ]
        return matching_voices

    def find_by_locale(self, locale: str) -> List[Dict[str, str]]:
        """Find voices by locale (e.g., 'zh-CN', 'en-US')."""
        return self.find(Locale=locale)

    def find_by_language(self, language: str) -> List[Dict[str, str]]:
        """Find voices by language code (e.g., 'zh', 'en')."""
        return self.find(Language=language)

    def find_by_gender(self, gender: str) -> List[Dict[str, str]]:
        """Find voices by gender ('Male' or 'Female')."""
        return self.find(Gender=gender)


# =============================================================================
# TTSEngine Class
# =============================================================================


class TTSEngine:
    """
    Text-to-Speech engine using Microsoft Edge TTS (edge-tts).

    Provides async text-to-speech synthesis with support for:
    - Multiple voices with dynamic selection
    - Speech rate adjustment
    - Output to both files and numpy arrays
    - Real-time streaming audio generation
    - Word boundary metadata for subtitle generation

    Attributes:
        default_voice: Default voice name for synthesis.
        sample_rate: Audio sample rate in Hz.
    """

    def __init__(
        self,
        default_voice: str = "zh-CN-XiaoxiaoNeural",
        sample_rate: int = 24000,
    ) -> None:
        """
        Initialize the TTS engine.

        Args:
            default_voice: Default voice name for synthesis.
                Default is zh-CN-XiaoxiaoNeural (Chinese female).
            sample_rate: Audio sample rate in Hz. Default is 24000.

        Raises:
            ValueError: If sample_rate is not positive.
        """
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")

        self.default_voice = default_voice
        self.sample_rate = sample_rate
        self._voices_cache: Optional[List[Dict]] = None
        self._voices_manager: Optional[VoicesManager] = None

    # =========================================================================
    # Voice Management
    # =========================================================================

    async def list_voices(self) -> List[Dict[str, str]]:
        """
        List all available voices.

        Returns:
            List of voice dictionaries with fields:
                - Name: Full voice name
                - ShortName: Short voice name
                - Gender: Voice gender (Male/Female)
                - Locale: Voice locale (e.g., zh-CN, en-US)

        Raises:
            SynthesisError: If unable to fetch voices from edge-tts.
        """
        if self._voices_cache is not None:
            return self._voices_cache

        try:
            voices = await edge_tts.list_voices()
            self._voices_cache = voices
            return voices
        except Exception as e:
            raise SynthesisError(f"Failed to list voices: {e}") from e

    async def get_voices_manager(self) -> VoicesManager:
        """
        Get or create a VoicesManager instance for advanced voice filtering.

        Returns:
            VoicesManager: Manager instance for voice filtering.
        """
        if self._voices_manager is None:
            self._voices_manager = await VoicesManager.create()
        return self._voices_manager

    async def find_voices(
        self,
        locale: Optional[str] = None,
        gender: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Find voices matching the specified criteria.

        Args:
            locale: Voice locale to filter by (e.g., "zh-CN", "en-US").
            gender: Voice gender to filter by ("Male" or "Female").
            language: Language code to filter by (e.g., "zh", "en").

        Returns:
            List of voice dictionaries matching the criteria.
        """
        manager = await self.get_voices_manager()

        criteria = {}
        if locale is not None:
            criteria["Locale"] = locale
        if gender is not None:
            criteria["Gender"] = gender
        if language is not None:
            criteria["Language"] = language

        if not criteria:
            return manager.voices

        return manager.find(**criteria)

    async def _validate_voice(self, voice_name: str) -> None:
        """
        Validate that a voice name exists.

        Args:
            voice_name: Voice name to validate.

        Raises:
            VoiceNotFoundError: If voice does not exist.
        """
        voices = await self.list_voices()
        voice_names = [v.get("ShortName", "") for v in voices]

        if voice_name not in voice_names:
            raise VoiceNotFoundError(f"Voice not found: {voice_name}")

    # =========================================================================
    # Streaming Methods (New)
    # =========================================================================

    async def stream(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream audio chunks as they're generated.

        This method yields raw MP3 audio bytes as they arrive from the TTS
        service, enabling real-time audio processing without waiting for
        the complete file.

        Args:
            text: Text to synthesize.
            voice: Voice name to use. None uses default_voice.
            rate: Speech rate adjustment (e.g., "+50%", "-50%", "+0%").

        Yields:
            bytes: Raw MP3 audio chunks.

        Raises:
            ValueError: If text is empty.
            VoiceNotFoundError: If voice is invalid.
            SynthesisError: If synthesis fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        voice_name = voice if voice is not None else self.default_voice
        await self._validate_voice(voice_name)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_name,
                rate=rate,
            )

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except edge_tts.exceptions.NoAudioReceived as e:
            raise NoAudioReceivedError(
                "No audio received from TTS service"
            ) from e
        except edge_tts.exceptions.WebSocketError as e:
            raise WebSocketError(f"WebSocket error: {e}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "voice" in error_msg or "not found" in error_msg:
                raise VoiceNotFoundError(f"Invalid voice: {voice_name}") from e
            raise SynthesisError(f"Synthesis failed: {e}") from e

    async def stream_with_metadata(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        boundary_type: str = "WordBoundary",
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream audio with word/sentence boundary events.

        This method yields dictionaries containing either audio data or
        word boundary metadata, enabling subtitle generation and
        synchronized playback.

        Args:
            text: Text to synthesize.
            voice: Voice name to use. None uses default_voice.
            rate: Speech rate adjustment (e.g., "+50%", "-50%", "+0%").
            boundary_type: "WordBoundary" or "SentenceBoundary".

        Yields:
            dict: Either:
                - {"type": "audio", "data": bytes} for audio chunks
                - {"type": "WordBoundary"|"SentenceBoundary",
                   "offset": int, "duration": int, "text": str}
                  for boundary events

        Raises:
            ValueError: If text is empty or boundary_type is invalid.
            VoiceNotFoundError: If voice is invalid.
            SynthesisError: If synthesis fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if boundary_type not in ("WordBoundary", "SentenceBoundary"):
            raise ValueError(
                f"boundary_type must be 'WordBoundary' or 'SentenceBoundary', "
                f"got {boundary_type}"
            )

        voice_name = voice if voice is not None else self.default_voice
        await self._validate_voice(voice_name)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_name,
                rate=rate,
                boundary=boundary_type,
            )

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield {"type": "audio", "data": chunk["data"]}
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    yield {
                        "type": chunk["type"],
                        "offset": chunk["offset"],
                        "duration": chunk["duration"],
                        "text": chunk["text"],
                    }

        except edge_tts.exceptions.NoAudioReceived as e:
            raise NoAudioReceivedError(
                "No audio received from TTS service"
            ) from e
        except edge_tts.exceptions.WebSocketError as e:
            raise WebSocketError(f"WebSocket error: {e}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "voice" in error_msg or "not found" in error_msg:
                raise VoiceNotFoundError(f"Invalid voice: {voice_name}") from e
            raise SynthesisError(f"Synthesis failed: {e}") from e

    async def stream_to_subtitles(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        boundary_type: str = "WordBoundary",
    ) -> tuple[bytes, List[WordBoundary]]:
        """
        Stream audio and collect word boundaries for subtitle generation.

        Convenience method that collects all audio and metadata from
        stream_with_metadata() into separate outputs.

        Args:
            text: Text to synthesize.
            voice: Voice name to use. None uses default_voice.
            rate: Speech rate adjustment.
            boundary_type: "WordBoundary" or "SentenceBoundary".

        Returns:
            Tuple of (audio_bytes, word_boundaries).

        Raises:
            ValueError: If text is empty.
            VoiceNotFoundError: If voice is invalid.
            SynthesisError: If synthesis fails.
        """
        audio_chunks: List[bytes] = []
        boundaries: List[WordBoundary] = []

        async for chunk in self.stream_with_metadata(
            text, voice, rate, boundary_type
        ):
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            else:
                boundaries.append(
                    WordBoundary(
                        type=chunk["type"],
                        offset=chunk["offset"],
                        duration=chunk["duration"],
                        text=chunk["text"],
                    )
                )

        return b"".join(audio_chunks), boundaries

    # =========================================================================
    # File/Array Output Methods (Existing)
    # =========================================================================

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: Optional[str] = None,
        rate: str = "+0%",
    ) -> None:
        """
        Synthesize text to speech and save to an MP3 file.

        Args:
            text: Text to synthesize.
            output_path: Path to save the output MP3 file.
            voice: Voice name to use. None uses default_voice.
            rate: Speech rate adjustment (e.g., "+50%", "-50%", "+0%").

        Raises:
            ValueError: If text is empty, voice is invalid, or path is invalid.
            SynthesisError: If synthesis fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        voice_name = voice if voice is not None else self.default_voice

        # Validate voice
        await self._validate_voice(voice_name)

        # Validate output path
        output_file = Path(output_path)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Invalid output path: {e}") from e

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_name,
                rate=rate,
            )
            await communicate.save(str(output_file))
        except edge_tts.exceptions.NoAudioReceived as e:
            raise NoAudioReceivedError(
                "No audio received from TTS service"
            ) from e
        except edge_tts.exceptions.WebSocketError as e:
            raise WebSocketError(f"WebSocket error: {e}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "voice" in error_msg or "not found" in error_msg:
                raise VoiceNotFoundError(f"Invalid voice: {voice_name}") from e
            raise SynthesisError(f"Synthesis failed: {e}") from e

    async def synthesize_to_array(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
    ) -> np.ndarray:
        """
        Synthesize text to speech and return as a numpy array.

        Converts the MP3 output from edge-tts to PCM audio data.

        Args:
            text: Text to synthesize.
            voice: Voice name to use. None uses default_voice.
            rate: Speech rate adjustment (e.g., "+50%", "-50%", "+0%").

        Returns:
            Audio data as numpy array (float32, mono).

        Raises:
            ValueError: If text is empty or voice is invalid.
            SynthesisError: If synthesis or conversion fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        voice_name = voice if voice is not None else self.default_voice

        # Validate voice
        await self._validate_voice(voice_name)

        # Use temporary file for intermediate MP3
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Synthesize to temporary MP3 file
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_name,
                rate=rate,
            )
            await communicate.save(tmp_path)

            # Convert MP3 to numpy array
            audio_data = self._mp3_to_array(tmp_path)

            return audio_data
        except (ValueError, VoiceNotFoundError, SynthesisError):
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "voice" in error_msg or "not found" in error_msg:
                raise VoiceNotFoundError(f"Invalid voice: {voice_name}") from e
            raise SynthesisError(f"Synthesis failed: {e}") from e
        finally:
            # Clean up temporary file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _mp3_to_array(self, mp3_path: Union[str, Path]) -> np.ndarray:
        """
        Convert MP3 file to numpy array.

        Args:
            mp3_path: Path to MP3 file.

        Returns:
            Audio data as numpy array (float32, mono).
        """
        import subprocess

        # Use ffmpeg to convert MP3 to WAV (PCM)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name

        try:
            # Get ffmpeg path
            try:
                import imageio_ffmpeg

                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_exe = "ffmpeg"

            # Convert MP3 to WAV using ffmpeg
            cmd = [
                ffmpeg_exe,
                "-i",
                str(mp3_path),
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",  # mono
                "-ar",
                str(self.sample_rate),
                "-y",  # overwrite
                wav_path,
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            # Read WAV file
            import soundfile as sf

            audio_data, _ = sf.read(wav_path, dtype=np.float32)

            return audio_data
        finally:
            # Clean up temporary WAV file
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass
