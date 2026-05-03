"""
Tests for VADDetector - Voice Activity Detection using webrtcvad.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.audio.vad_detector import VADDetector


class TestVADDetectorInit:
    """Test VADDetector initialization."""

    def test_init_default_aggressiveness(self):
        """Test initialization with default aggressiveness mode."""
        detector = VADDetector()
        assert detector.aggressiveness == 3

    def test_init_with_aggressiveness_0(self):
        """Test initialization with aggressiveness mode 0 (quality)."""
        detector = VADDetector(aggressiveness=0)
        assert detector.aggressiveness == 0

    def test_init_with_aggressiveness_1(self):
        """Test initialization with aggressiveness mode 1."""
        detector = VADDetector(aggressiveness=1)
        assert detector.aggressiveness == 1

    def test_init_with_aggressiveness_2(self):
        """Test initialization with aggressiveness mode 2."""
        detector = VADDetector(aggressiveness=2)
        assert detector.aggressiveness == 2

    def test_init_with_aggressiveness_3(self):
        """Test initialization with aggressiveness mode 3 (aggressive)."""
        detector = VADDetector(aggressiveness=3)
        assert detector.aggressiveness == 3

    def test_init_invalid_aggressiveness_negative(self):
        """Test initialization with invalid negative aggressiveness."""
        with pytest.raises(ValueError, match="aggressiveness must be between 0 and 3"):
            VADDetector(aggressiveness=-1)

    def test_init_invalid_aggressiveness_too_high(self):
        """Test initialization with invalid high aggressiveness."""
        with pytest.raises(ValueError, match="aggressiveness must be between 0 and 3"):
            VADDetector(aggressiveness=4)


class TestVADDetectorFrameSizeValidation:
    """Test frame size validation for VAD detection."""

    def test_valid_frame_size_10ms(self):
        """Test that 10ms frame size is accepted."""
        detector = VADDetector()
        # 10ms at 16kHz = 160 samples
        frame = np.zeros(160, dtype=np.int16)
        # Should not raise
        detector.is_speech(frame, frame_duration_ms=10)

    def test_valid_frame_size_20ms(self):
        """Test that 20ms frame size is accepted."""
        detector = VADDetector()
        # 20ms at 16kHz = 320 samples
        frame = np.zeros(320, dtype=np.int16)
        detector.is_speech(frame)

    def test_valid_frame_size_30ms(self):
        """Test that 30ms frame size is accepted."""
        detector = VADDetector()
        # 30ms at 16kHz = 480 samples
        frame = np.zeros(480, dtype=np.int16)
        detector.is_speech(frame, frame_duration_ms=30)

    def test_invalid_frame_size(self):
        """Test that invalid frame size raises error."""
        detector = VADDetector()
        # 15ms at 16kHz = 240 samples (invalid)
        frame = np.zeros(240, dtype=np.int16)
        with pytest.raises(ValueError, match="Frame duration must be 10, 20, or 30 ms"):
            detector.is_speech(frame)


class TestVADDetectorIsSpeech:
    """Test voice activity detection on audio frames."""

    def test_is_speech_silence(self):
        """Test detection on silent audio."""
        detector = VADDetector(aggressiveness=3)
        # Silent frame (all zeros)
        frame = np.zeros(320, dtype=np.int16)
        result = detector.is_speech(frame)
        assert result is False

    def test_is_speech_with_noise(self):
        """Test detection on noisy audio."""
        detector = VADDetector(aggressiveness=0)
        # Generate noise-like signal
        np.random.seed(42)
        frame = (np.random.randn(320) * 1000).astype(np.int16)
        # Result depends on VAD algorithm, just verify it returns bool
        result = detector.is_speech(frame)
        assert isinstance(result, bool)

    def test_is_speech_with_loud_signal(self):
        """Test detection on loud audio signal."""
        detector = VADDetector(aggressiveness=0)
        # Generate loud signal (sine wave at 440Hz)
        t = np.linspace(0, 0.02, 320)
        frame = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
        result = detector.is_speech(frame)
        assert isinstance(result, bool)

    def test_is_speech_wrong_sample_rate_raises(self):
        """Test that wrong sample rate raises error."""
        detector = VADDetector()
        # Frame size for 44.1kHz would be different
        frame = np.zeros(320, dtype=np.int16)
        # VADDetector expects 16kHz, this should work
        # But if we pass wrong sample_rate parameter it should fail
        with pytest.raises(ValueError, match="Sample rate must be 16000"):
            detector.is_speech(frame, sample_rate=44100)

    def test_is_speech_invalid_audio_format(self):
        """Test that invalid audio format raises error."""
        detector = VADDetector()
        # Float32 instead of int16
        frame = np.zeros(320, dtype=np.float32)
        with pytest.raises(ValueError, match="Audio must be 16-bit PCM"):
            detector.is_speech(frame)


class TestVADDetectorProcessStream:
    """Test processing continuous audio stream."""

    def test_process_stream_empty(self):
        """Test processing empty audio stream."""
        detector = VADDetector()
        audio = np.array([], dtype=np.int16)
        results = list(detector.process_stream(audio))
        assert results == []

    def test_process_stream_single_frame(self):
        """Test processing single audio frame."""
        detector = VADDetector()
        # Single 20ms frame
        audio = np.zeros(320, dtype=np.int16)
        results = list(detector.process_stream(audio))
        assert len(results) == 1
        assert isinstance(results[0], bool)

    def test_process_stream_multiple_frames(self):
        """Test processing multiple audio frames."""
        detector = VADDetector()
        # 3 frames of 20ms each
        audio = np.zeros(320 * 3, dtype=np.int16)
        results = list(detector.process_stream(audio))
        assert len(results) == 3

    def test_process_stream_partial_frame_ignored(self):
        """Test that partial frames at the end are ignored."""
        detector = VADDetector()
        # 2.5 frames of 20ms
        audio = np.zeros(320 * 2 + 160, dtype=np.int16)
        results = list(detector.process_stream(audio))
        assert len(results) == 2

    def test_process_stream_with_different_frame_duration(self):
        """Test processing stream with custom frame duration."""
        detector = VADDetector()
        # 2 frames of 30ms
        audio = np.zeros(480 * 2, dtype=np.int16)
        results = list(detector.process_stream(audio, frame_duration_ms=30))
        assert len(results) == 2


class TestVADDetectorSpeechSegments:
    """Test getting speech segments from audio."""

    def test_get_speech_segments_empty(self):
        """Test getting segments from empty audio."""
        detector = VADDetector()
        audio = np.array([], dtype=np.int16)
        segments = detector.get_speech_segments(audio)
        assert segments == []

    def test_get_speech_segments_silence(self):
        """Test getting segments from silent audio."""
        detector = VADDetector(aggressiveness=3)
        # 1 second of silence
        audio = np.zeros(16000, dtype=np.int16)
        segments = detector.get_speech_segments(audio)
        assert segments == []

    def test_get_speech_segments_returns_list(self):
        """Test that get_speech_segments returns a list."""
        detector = VADDetector()
        audio = np.zeros(16000, dtype=np.int16)
        segments = detector.get_speech_segments(audio)
        assert isinstance(segments, list)

    def test_get_speech_segments_format(self):
        """Test that segments are returned as (start, end) tuples."""
        detector = VADDetector(aggressiveness=0)
        # Create audio with some "speech-like" content
        np.random.seed(42)
        audio = (np.random.randn(16000) * 5000).astype(np.int16)
        segments = detector.get_speech_segments(audio)
        # Each segment should be a tuple of (start_time, end_time)
        for segment in segments:
            assert isinstance(segment, tuple)
            assert len(segment) == 2
            assert isinstance(segment[0], float)  # start time
            assert isinstance(segment[1], float)  # end time
            assert segment[0] < segment[1]  # start < end


class TestVADDetectorContextManager:
    """Test context manager support."""

    def test_context_manager_enter_exit(self):
        """Test that VADDetector works as context manager."""
        with VADDetector() as detector:
            assert detector is not None
            frame = np.zeros(320, dtype=np.int16)
            result = detector.is_speech(frame)
            assert isinstance(result, bool)

    def test_context_manager_returns_self(self):
        """Test that __enter__ returns self."""
        detector = VADDetector()
        with detector as ctx_detector:
            assert ctx_detector is detector


class TestVADDetectorErrorHandling:
    """Test error handling."""

    def test_is_speech_none_input(self):
        """Test that None input raises appropriate error."""
        detector = VADDetector()
        with pytest.raises((TypeError, ValueError)):
            detector.is_speech(None)

    def test_is_speech_wrong_dimensions(self):
        """Test that multi-dimensional array raises error."""
        detector = VADDetector()
        frame = np.zeros((320, 2), dtype=np.int16)
        with pytest.raises(ValueError, match="Audio must be mono"):
            detector.is_speech(frame)

    def test_process_stream_invalid_frame_duration(self):
        """Test that invalid frame duration raises error."""
        detector = VADDetector()
        audio = np.zeros(320, dtype=np.int16)
        with pytest.raises(ValueError, match="Frame duration must be 10, 20, or 30 ms"):
            list(detector.process_stream(audio, frame_duration_ms=15))


class TestVADDetectorSampleRate:
    """Test sample rate handling."""

    def test_sample_rate_property(self):
        """Test that sample_rate property returns 16000."""
        detector = VADDetector()
        assert detector.sample_rate == 16000

    def test_sample_rate_is_readonly(self):
        """Test that sample_rate cannot be modified."""
        detector = VADDetector()
        with pytest.raises(AttributeError):
            detector.sample_rate = 44100
