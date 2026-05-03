"""
TTSEngine tests - TDD approach
Tests written first, implementation follows.
"""
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from src.audio.tts_engine import TTSEngine


class TestTTSEngineInitialization:
    """Test TTSEngine initialization with default and custom parameters."""

    def test_default_initialization(self) -> None:
        """Test initialization with default voice."""
        engine = TTSEngine()
        assert engine.default_voice == "zh-CN-XiaoxiaoNeural"
        assert engine.sample_rate == 24000

    def test_custom_initialization(self) -> None:
        """Test initialization with custom voice."""
        engine = TTSEngine(default_voice="en-US-JennyNeural", sample_rate=16000)
        assert engine.default_voice == "en-US-JennyNeural"
        assert engine.sample_rate == 16000

    def test_invalid_sample_rate_raises_error(self) -> None:
        """Test that invalid sample rate raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            TTSEngine(sample_rate=0)

    def test_negative_sample_rate_raises_error(self) -> None:
        """Test that negative sample rate raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            TTSEngine(sample_rate=-24000)


class TestTTSEngineListVoices:
    """Test listing available voices."""

    @pytest.mark.asyncio
    async def test_list_voices_returns_list(self) -> None:
        """Test that list_voices returns a list of voice dictionaries."""
        engine = TTSEngine()
        voices = await engine.list_voices()
        assert isinstance(voices, list)
        assert len(voices) > 0

    @pytest.mark.asyncio
    async def test_list_voices_contains_required_fields(self) -> None:
        """Test that each voice has required fields."""
        engine = TTSEngine()
        voices = await engine.list_voices()
        for voice in voices:
            assert "Name" in voice
            assert "ShortName" in voice
            assert "Gender" in voice
            assert "Locale" in voice

    @pytest.mark.asyncio
    async def test_list_voices_contains_default_voice(self) -> None:
        """Test that the default voice is in the list."""
        engine = TTSEngine()
        voices = await engine.list_voices()
        voice_names = [v["ShortName"] for v in voices]
        assert "zh-CN-XiaoxiaoNeural" in voice_names


class TestTTSEngineSynthesizeToFile:
    """Test text-to-speech synthesis to file."""

    @pytest.mark.asyncio
    async def test_synthesize_to_file_creates_mp3(self, tmp_path: Path) -> None:
        """Test that synthesize_to_file creates an MP3 file."""
        engine = TTSEngine()
        output_file = tmp_path / "output.mp3"
        await engine.synthesize_to_file("你好世界", str(output_file))
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_synthesize_to_file_with_custom_voice(self, tmp_path: Path) -> None:
        """Test synthesis with a custom voice."""
        engine = TTSEngine()
        output_file = tmp_path / "output.mp3"
        await engine.synthesize_to_file(
            "Hello world", str(output_file), voice="en-US-JennyNeural"
        )
        assert output_file.exists()

    @pytest.mark.asyncio
    async def test_synthesize_to_file_with_rate_adjustment(self, tmp_path: Path) -> None:
        """Test synthesis with speech rate adjustment."""
        engine = TTSEngine()
        output_file = tmp_path / "output.mp3"
        await engine.synthesize_to_file("测试语速", str(output_file), rate="+50%")
        assert output_file.exists()

        output_file2 = tmp_path / "output2.mp3"
        await engine.synthesize_to_file("测试语速", str(output_file2), rate="-50%")
        assert output_file2.exists()

    @pytest.mark.asyncio
    async def test_synthesize_to_file_empty_text_raises_error(self, tmp_path: Path) -> None:
        """Test that empty text raises ValueError."""
        engine = TTSEngine()
        output_file = tmp_path / "output.mp3"
        with pytest.raises(ValueError, match="empty"):
            await engine.synthesize_to_file("", str(output_file))

    @pytest.mark.asyncio
    async def test_synthesize_to_file_invalid_voice_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid voice raises ValueError."""
        engine = TTSEngine()
        output_file = tmp_path / "output.mp3"
        with pytest.raises(ValueError, match="voice"):
            await engine.synthesize_to_file("测试", str(output_file), voice="InvalidVoice")

    @pytest.mark.asyncio
    async def test_synthesize_to_file_invalid_path_raises_error(self) -> None:
        """Test that invalid file path raises ValueError."""
        engine = TTSEngine()
        # Use a path with invalid characters on Windows
        with pytest.raises((ValueError, OSError)):
            await engine.synthesize_to_file("测试", "/invalid<>path/output.mp3")


class TestTTSEngineSynthesizeToArray:
    """Test text-to-speech synthesis to numpy array."""

    @pytest.mark.asyncio
    async def test_synthesize_to_array_returns_numpy_array(self) -> None:
        """Test that synthesize_to_array returns a numpy array."""
        engine = TTSEngine()
        audio_data = await engine.synthesize_to_array("你好世界")
        assert isinstance(audio_data, np.ndarray)
        assert len(audio_data) > 0

    @pytest.mark.asyncio
    async def test_synthesize_to_array_is_float32(self) -> None:
        """Test that audio data is float32."""
        engine = TTSEngine()
        audio_data = await engine.synthesize_to_array("测试音频")
        assert audio_data.dtype == np.float32

    @pytest.mark.asyncio
    async def test_synthesize_to_array_with_custom_voice(self) -> None:
        """Test synthesis to array with custom voice."""
        engine = TTSEngine()
        audio_data = await engine.synthesize_to_array(
            "Hello world", voice="en-US-JennyNeural"
        )
        assert isinstance(audio_data, np.ndarray)
        assert len(audio_data) > 0

    @pytest.mark.asyncio
    async def test_synthesize_to_array_with_rate_adjustment(self) -> None:
        """Test synthesis to array with rate adjustment."""
        engine = TTSEngine()
        audio_data = await engine.synthesize_to_array("测试语速", rate="+50%")
        assert isinstance(audio_data, np.ndarray)
        assert len(audio_data) > 0

    @pytest.mark.asyncio
    async def test_synthesize_to_array_empty_text_raises_error(self) -> None:
        """Test that empty text raises ValueError."""
        engine = TTSEngine()
        with pytest.raises(ValueError, match="empty"):
            await engine.synthesize_to_array("")

    @pytest.mark.asyncio
    async def test_synthesize_to_array_invalid_voice_raises_error(self) -> None:
        """Test that invalid voice raises ValueError."""
        engine = TTSEngine()
        with pytest.raises(ValueError, match="voice"):
            await engine.synthesize_to_array("测试", voice="InvalidVoice")


class TestTTSEngineVoiceSelection:
    """Test voice selection functionality."""

    @pytest.mark.asyncio
    async def test_find_voice_by_locale(self) -> None:
        """Test finding voices by locale."""
        engine = TTSEngine()
        voices = await engine.find_voices(locale="zh-CN")
        assert isinstance(voices, list)
        assert len(voices) > 0
        for voice in voices:
            assert "zh-CN" in voice["Locale"]

    @pytest.mark.asyncio
    async def test_find_voice_by_gender(self) -> None:
        """Test finding voices by gender."""
        engine = TTSEngine()
        voices = await engine.find_voices(gender="Female")
        assert isinstance(voices, list)
        assert len(voices) > 0
        for voice in voices:
            assert voice["Gender"] == "Female"

    @pytest.mark.asyncio
    async def test_find_voice_by_locale_and_gender(self) -> None:
        """Test finding voices by locale and gender."""
        engine = TTSEngine()
        voices = await engine.find_voices(locale="en-US", gender="Male")
        assert isinstance(voices, list)
        assert len(voices) > 0
        for voice in voices:
            assert "en-US" in voice["Locale"]
            assert voice["Gender"] == "Male"


class TestTTSEngineErrorHandling:
    """Test error handling for various failure scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Read-only directory test not reliable on Windows"
    )
    async def test_synthesize_to_file_write_error(self, tmp_path: Path) -> None:
        """Test handling of file write errors."""
        engine = TTSEngine()
        # Create a read-only directory to trigger write error
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        output_file = readonly_dir / "output.mp3"

        # Make directory read-only (this may not work on all systems)
        try:
            import os
            os.chmod(str(readonly_dir), 0o444)
            with pytest.raises(ValueError, match="path|write"):
                await engine.synthesize_to_file("测试", str(output_file))
        finally:
            # Restore permissions for cleanup
            import os
            os.chmod(str(readonly_dir), 0o755)

    def test_invalid_voice_name_format(self) -> None:
        """Test that invalid voice name format is handled."""
        engine = TTSEngine(default_voice="InvalidFormat")
        # Should not raise during initialization
        assert engine.default_voice == "InvalidFormat"


class TestTTSEngineAsyncSupport:
    """Test async support and concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_synthesis(self, tmp_path: Path) -> None:
        """Test concurrent synthesis operations."""
        import asyncio

        engine = TTSEngine()

        async def synthesize_one(text: str, index: int) -> Path:
            output_file = tmp_path / f"output_{index}.mp3"
            await engine.synthesize_to_file(text, str(output_file))
            return output_file

        # Run multiple synthesis tasks concurrently
        tasks = [
            synthesize_one("测试一", 1),
            synthesize_one("测试二", 2),
            synthesize_one("测试三", 3),
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert result.exists()

    @pytest.mark.asyncio
    async def test_multiple_array_synthesis(self) -> None:
        """Test multiple synthesis to array operations."""
        engine = TTSEngine()

        audio1 = await engine.synthesize_to_array("第一段")
        audio2 = await engine.synthesize_to_array("第二段")

        assert isinstance(audio1, np.ndarray)
        assert isinstance(audio2, np.ndarray)
        assert len(audio1) > 0
        assert len(audio2) > 0
