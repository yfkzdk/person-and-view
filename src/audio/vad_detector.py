"""
VADDetector - Voice Activity Detection using webrtcvad.
"""
from typing import List, Tuple, Iterator, Optional
from dataclasses import dataclass
from collections import deque
import numpy as np
import webrtcvad


@dataclass
class Frame:
    """
    Represents a frame of audio data with metadata.

    Attributes:
        bytes: Audio data as bytes (16-bit PCM).
        timestamp: Start time in seconds.
        duration: Frame duration in seconds.
    """
    bytes: bytes
    timestamp: float
    duration: float


class VADDetector:
    """
    Voice Activity Detector using WebRTC VAD.

    Provides voice activity detection for audio signals using the
    WebRTC VAD algorithm. Requires 16kHz sample rate and 16-bit PCM audio.

    Attributes:
        aggressiveness: VAD filtering mode (0=quality, 3=aggressive).
        sample_rate: Audio sample rate (always 16000 Hz).
    """

    SAMPLE_RATE = 16000
    VALID_FRAME_DURATIONS = (10, 20, 30)  # milliseconds

    def __init__(self, aggressiveness: int = 3) -> None:
        """
        Initialize the VAD detector.

        Args:
            aggressiveness: Filtering mode from 0 to 3.
                0 = least aggressive (best for quality)
                3 = most aggressive (best for filtering)

        Raises:
            ValueError: If aggressiveness is not between 0 and 3.
        """
        if not 0 <= aggressiveness <= 3:
            raise ValueError(
                f"aggressiveness must be between 0 and 3, got {aggressiveness}"
            )

        self._aggressiveness = aggressiveness
        self._vad = webrtcvad.Vad(aggressiveness)

    @property
    def aggressiveness(self) -> int:
        """Get the aggressiveness mode."""
        return self._aggressiveness

    @property
    def sample_rate(self) -> int:
        """Get the required sample rate (16kHz)."""
        return self.SAMPLE_RATE

    def _validate_frame_duration(self, frame_duration_ms: int) -> None:
        """
        Validate frame duration.

        Args:
            frame_duration_ms: Frame duration in milliseconds.

        Raises:
            ValueError: If frame duration is not 10, 20, or 30 ms.
        """
        if frame_duration_ms not in self.VALID_FRAME_DURATIONS:
            raise ValueError(
                f"Frame duration must be 10, 20, or 30 ms, got {frame_duration_ms} ms"
            )

    def _get_frame_size(self, frame_duration_ms: int) -> int:
        """
        Calculate frame size in samples.

        Args:
            frame_duration_ms: Frame duration in milliseconds.

        Returns:
            Number of samples per frame.
        """
        return int(self.SAMPLE_RATE * frame_duration_ms / 1000)

    def frame_generator(
        self,
        audio: bytes,
        frame_duration_ms: int = 30,
    ) -> Iterator[Frame]:
        """
        Generate audio frames from PCM audio data.

        Args:
            audio: Audio data as bytes (16-bit PCM, mono).
            frame_duration_ms: Frame duration in ms (10, 20, or 30).

        Yields:
            Frame objects with audio data, timestamp, and duration.

        Raises:
            ValueError: If frame duration is invalid.
        """
        self._validate_frame_duration(frame_duration_ms)

        # Calculate byte size per frame (2 bytes per sample for 16-bit audio)
        n = int(self.SAMPLE_RATE * (frame_duration_ms / 1000.0) * 2)
        duration = frame_duration_ms / 1000.0
        timestamp = 0.0
        offset = 0

        while offset + n <= len(audio):
            yield Frame(
                bytes=audio[offset:offset + n],
                timestamp=timestamp,
                duration=duration,
            )
            timestamp += duration
            offset += n

    def vad_collector(
        self,
        frames: Iterator[Frame],
        frame_duration_ms: int = 30,
        padding_duration_ms: int = 300,
    ) -> Iterator[Tuple[float, float, bytes]]:
        """
        Collect voiced audio segments using sliding window + state machine.

        Uses a ring buffer with 90% threshold for robust speech detection.
        This prevents false triggers from brief noise and ensures clean
        segment boundaries.

        Args:
            frames: Iterator of Frame objects.
            frame_duration_ms: Frame duration in ms (10, 20, or 30).
            padding_duration_ms: Padding duration in ms (default 300ms).

        Yields:
            Tuples of (start_time, end_time, audio_bytes) for each segment.

        Raises:
            ValueError: If frame duration is invalid.
        """
        self._validate_frame_duration(frame_duration_ms)

        num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        ring_buffer: deque = deque(maxlen=num_padding_frames)
        triggered = False
        voiced_frames: List[Frame] = []

        for frame in frames:
            is_speech = self._vad.is_speech(frame.bytes, self.SAMPLE_RATE)

            if not triggered:
                # Not in speech segment - accumulate frames in ring buffer
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])

                # 90% threshold for triggering
                if num_voiced > 0.9 * ring_buffer.maxlen:
                    triggered = True
                    # Collect all buffered frames
                    for f, s in ring_buffer:
                        voiced_frames.append(f)
                    ring_buffer.clear()
            else:
                # In speech segment - collect frame
                voiced_frames.append(frame)
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])

                # 90% threshold for de-triggering
                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    triggered = False
                    # Yield the segment
                    if voiced_frames:
                        start_time = voiced_frames[0].timestamp
                        end_time = voiced_frames[-1].timestamp + voiced_frames[-1].duration
                        audio_bytes = b''.join([f.bytes for f in voiced_frames])
                        yield (start_time, end_time, audio_bytes)
                    ring_buffer.clear()
                    voiced_frames = []

        # Yield remaining voiced frames at the end
        if voiced_frames:
            start_time = voiced_frames[0].timestamp
            end_time = voiced_frames[-1].timestamp + voiced_frames[-1].duration
            audio_bytes = b''.join([f.bytes for f in voiced_frames])
            yield (start_time, end_time, audio_bytes)

    def is_speech(
        self,
        frame: np.ndarray,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
    ) -> bool:
        """
        Detect if an audio frame contains speech.

        Args:
            frame: Audio frame as numpy array (16-bit PCM, mono).
            sample_rate: Sample rate (must be 16000).
            frame_duration_ms: Frame duration in ms (10, 20, or 30).

        Returns:
            True if speech is detected, False otherwise.

        Raises:
            ValueError: If sample rate is not 16000.
            ValueError: If audio is not 16-bit PCM.
            ValueError: If audio is not mono.
            ValueError: If frame duration is invalid.
        """
        if sample_rate != self.SAMPLE_RATE:
            raise ValueError(
                f"Sample rate must be {self.SAMPLE_RATE}, got {sample_rate}"
            )

        self._validate_frame_duration(frame_duration_ms)

        if frame is None:
            raise ValueError("Audio frame cannot be None")

        if frame.dtype != np.int16:
            raise ValueError(
                f"Audio must be 16-bit PCM (int16), got {frame.dtype}"
            )

        if frame.ndim != 1:
            raise ValueError(f"Audio must be mono (1D array), got {frame.ndim}D")

        # Validate frame size matches expected duration
        expected_frame_size = self._get_frame_size(frame_duration_ms)
        if len(frame) != expected_frame_size:
            actual_duration_ms = len(frame) * 1000 // self.SAMPLE_RATE
            raise ValueError(
                f"Frame duration must be 10, 20, or 30 ms, "
                f"got {actual_duration_ms} ms ({len(frame)} samples)"
            )

        # Convert to bytes for webrtcvad
        audio_bytes = frame.tobytes()

        return self._vad.is_speech(audio_bytes, self.SAMPLE_RATE)

    def process_stream(
        self,
        audio: np.ndarray,
        frame_duration_ms: int = 20,
    ) -> Iterator[bool]:
        """
        Process a continuous audio stream and yield speech detection results.

        Args:
            audio: Audio data as numpy array (16-bit PCM, mono).
            frame_duration_ms: Frame duration in ms (10, 20, or 30).

        Yields:
            Boolean indicating speech presence for each frame.

        Raises:
            ValueError: If frame duration is invalid.
            ValueError: If audio is not 16-bit PCM.
            ValueError: If audio is not mono.
        """
        self._validate_frame_duration(frame_duration_ms)

        if audio is None or len(audio) == 0:
            return

        if audio.dtype != np.int16:
            raise ValueError(
                f"Audio must be 16-bit PCM (int16), got {audio.dtype}"
            )

        if audio.ndim != 1:
            raise ValueError(f"Audio must be mono (1D array), got {audio.ndim}D")

        frame_size = self._get_frame_size(frame_duration_ms)
        num_frames = len(audio) // frame_size

        for i in range(num_frames):
            start = i * frame_size
            end = start + frame_size
            frame = audio[start:end]
            yield self.is_speech(frame, frame_duration_ms=frame_duration_ms)

    def get_speech_segments(
        self,
        audio: np.ndarray,
        frame_duration_ms: int = 30,
        padding_duration_ms: int = 300,
    ) -> List[Tuple[float, float]]:
        """
        Extract speech segments from continuous audio using sliding window algorithm.

        Uses the robust vad_collector algorithm with ring buffer and 90% threshold
        for reliable speech segment detection.

        Args:
            audio: Audio data as numpy array (16-bit PCM, mono).
            frame_duration_ms: Frame duration in ms (10, 20, or 30).
            padding_duration_ms: Padding duration in ms (default 300ms).

        Returns:
            List of (start_time, end_time) tuples in seconds.

        Raises:
            ValueError: If frame duration is invalid.
            ValueError: If audio is not 16-bit PCM.
            ValueError: If audio is not mono.
        """
        if audio is None or len(audio) == 0:
            return []

        self._validate_frame_duration(frame_duration_ms)

        if audio.dtype != np.int16:
            raise ValueError(
                f"Audio must be 16-bit PCM (int16), got {audio.dtype}"
            )

        if audio.ndim != 1:
            raise ValueError(f"Audio must be mono (1D array), got {audio.ndim}D")

        # Convert numpy array to bytes for frame generator
        audio_bytes = audio.tobytes()

        # Generate frames
        frames = self.frame_generator(audio_bytes, frame_duration_ms)

        # Collect speech segments
        segments: List[Tuple[float, float]] = []
        for start_time, end_time, _ in self.vad_collector(
            frames, frame_duration_ms, padding_duration_ms
        ):
            segments.append((start_time, end_time))

        return segments

    def get_speech_segments_with_audio(
        self,
        audio: np.ndarray,
        frame_duration_ms: int = 30,
        padding_duration_ms: int = 300,
    ) -> List[Tuple[float, float, bytes]]:
        """
        Extract speech segments with audio data from continuous audio.

        Uses the robust vad_collector algorithm with ring buffer and 90% threshold.

        Args:
            audio: Audio data as numpy array (16-bit PCM, mono).
            frame_duration_ms: Frame duration in ms (10, 20, or 30).
            padding_duration_ms: Padding duration in ms (default 300ms).

        Returns:
            List of (start_time, end_time, audio_bytes) tuples.

        Raises:
            ValueError: If frame duration is invalid.
            ValueError: If audio is not 16-bit PCM.
            ValueError: If audio is not mono.
        """
        if audio is None or len(audio) == 0:
            return []

        self._validate_frame_duration(frame_duration_ms)

        if audio.dtype != np.int16:
            raise ValueError(
                f"Audio must be 16-bit PCM (int16), got {audio.dtype}"
            )

        if audio.ndim != 1:
            raise ValueError(f"Audio must be mono (1D array), got {audio.ndim}D")

        # Convert numpy array to bytes for frame generator
        audio_bytes = audio.tobytes()

        # Generate frames
        frames = self.frame_generator(audio_bytes, frame_duration_ms)

        # Collect speech segments with audio
        segments: List[Tuple[float, float, bytes]] = []
        for segment in self.vad_collector(frames, frame_duration_ms, padding_duration_ms):
            segments.append(segment)

        return segments

    def __enter__(self) -> "VADDetector":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager."""
        return False
