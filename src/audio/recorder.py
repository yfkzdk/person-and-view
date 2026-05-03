"""
AudioRecorder - Real-time audio recording with sounddevice

Refactored with best practices from python-sounddevice reference project.
"""
import logging
import queue
import threading
from typing import Optional, List, Dict, Any

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioRecorderError(Exception):
    """Base exception for AudioRecorder errors."""
    pass


class DeviceNotFoundError(AudioRecorderError):
    """Raised when the specified audio device is not found."""
    pass


class DeviceIncompatibleError(AudioRecorderError):
    """Raised when the device doesn't support required capabilities."""
    pass


class AudioRecorder:
    """
    Real-time audio recorder using sounddevice.

    Supports configurable sample rate, channels, and chunk size.
    Provides recording control (start, stop, pause, resume) and
    volume detection via RMS calculation.

    Implements best practices from python-sounddevice reference:
    - Device capability validation before stream start
    - Queue-based buffering for thread-safe audio capture
    - Status flag checking in callbacks
    - Proper cleanup with context managers and __del__

    Attributes:
        sample_rate: Audio sample rate in Hz.
        channels: Number of audio channels (1=mono, 2=stereo).
        chunk_size: Number of samples per audio chunk.
        device: Audio device index (None for default).
        buffer_size: Maximum number of chunks in the queue.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        device: Optional[int] = None,
        buffer_size: int = 100,
    ) -> None:
        """
        Initialize the audio recorder.

        Args:
            sample_rate: Audio sample rate in Hz. Default is 16000.
                If 0, will auto-detect from device default.
            channels: Number of audio channels. Default is 1 (mono).
            chunk_size: Number of samples per chunk. Default is 1024.
            device: Audio device index. None uses the default device.
            buffer_size: Maximum chunks in queue. Default is 100.

        Raises:
            ValueError: If any parameter is invalid.
        """
        if sample_rate < 0:
            raise ValueError(f"sample_rate must be non-negative, got {sample_rate}")
        if channels <= 0:
            raise ValueError(f"channels must be positive, got {channels}")
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if buffer_size <= 0:
            raise ValueError(f"buffer_size must be positive, got {buffer_size}")

        self._sample_rate = sample_rate
        self._channels = channels
        self.chunk_size = chunk_size
        self.device = device
        self.buffer_size = buffer_size

        self._is_recording = False
        self._is_paused = False
        self._audio_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._audio_data: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._status_flags: List[str] = []  # Track status issues for debugging

    @property
    def sample_rate(self) -> int:
        """Get the sample rate (auto-detected if was 0)."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Get the number of channels."""
        return self._channels

    @property
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._is_recording

    @property
    def is_paused(self) -> bool:
        """Check if recording is paused."""
        return self._is_paused

    @staticmethod
    def get_device_list() -> List[Dict[str, Any]]:
        """
        Get a list of all available audio input devices.

        Returns:
            List of dictionaries containing device information.
            Each dict has keys: 'index', 'name', 'max_input_channels',
            'default_samplerate', 'default_low_input_latency'.
        """
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': dev['name'],
                    'max_input_channels': dev['max_input_channels'],
                    'default_samplerate': dev['default_samplerate'],
                    'default_low_input_latency': dev['default_low_input_latency'],
                })
        return devices

    def query_device_info(self) -> Dict[str, Any]:
        """
        Query the capabilities of the configured audio device.

        Returns:
            Dictionary with device capabilities including:
            - name: Device name
            - max_input_channels: Maximum input channels
            - default_samplerate: Default sample rate
            - default_low_input_latency: Default low latency

        Raises:
            DeviceNotFoundError: If the device doesn't exist.
        """
        try:
            device_info = sd.query_devices(self.device, 'input')
            return {
                'name': device_info['name'],
                'max_input_channels': device_info['max_input_channels'],
                'default_samplerate': int(device_info['default_samplerate']),
                'default_low_input_latency': device_info['default_low_input_latency'],
            }
        except ValueError as e:
            raise DeviceNotFoundError(
                f"Audio device {self.device} not found: {e}"
            ) from e

    def _validate_device(self) -> None:
        """
        Validate that the device supports required configuration.

        Raises:
            DeviceNotFoundError: If device doesn't exist.
            DeviceIncompatibleError: If device lacks required capabilities.
        """
        device_info = self.query_device_info()

        # Check input channels
        if device_info['max_input_channels'] < self._channels:
            raise DeviceIncompatibleError(
                f"Device '{device_info['name']}' only supports "
                f"{device_info['max_input_channels']} input channels, "
                f"but {self._channels} requested."
            )

        # Auto-detect sample rate if not specified
        if self._sample_rate == 0:
            self._sample_rate = device_info['default_samplerate']
            logger.info(
                f"Auto-detected sample rate: {self._sample_rate} Hz "
                f"for device '{device_info['name']}'"
            )

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """
        Callback function for audio stream to capture data.

        Implements best practices:
        - Checks status flags for overflow/underflow
        - Uses non-blocking queue operations
        - Logs status conditions for debugging

        Args:
            indata: Input audio data buffer.
            frames: Number of frames.
            time: Timing information.
            status: Status flags indicating stream conditions.
        """
        # Check and log status flags
        if status:
            status_msg = []
            if status.input_overflow:
                status_msg.append("input_overflow")
            if status.input_underflow:
                status_msg.append("input_underflow")
            if status_msg:
                logger.warning(f"Audio callback status: {', '.join(status_msg)}")
                with self._lock:
                    self._status_flags.extend(status_msg)

        if self._is_paused:
            return

        # Use non-blocking put to avoid blocking the audio thread
        try:
            self._audio_queue.put_nowait(indata.copy())
        except queue.Full:
            # Queue is full - drop oldest chunk and add new one
            # This prevents blocking the audio thread
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(indata.copy())
                logger.debug("Audio queue full, dropped oldest chunk")
            except queue.Empty:
                # Race condition - queue became empty, just put the data
                self._audio_queue.put_nowait(indata.copy())

    def _drain_queue(self) -> None:
        """Drain the audio queue into the audio data list."""
        while True:
            try:
                chunk = self._audio_queue.get_nowait()
                with self._lock:
                    self._audio_data.append(chunk)
            except queue.Empty:
                break

    def start(self) -> None:
        """
        Start recording audio.

        Validates device capabilities before starting the stream.

        Raises:
            RuntimeError: If already recording.
            DeviceNotFoundError: If the audio device is not found.
            DeviceIncompatibleError: If the device lacks required capabilities.
            sd.PortAudioError: If PortAudio encounters an error.
        """
        if self._is_recording:
            raise RuntimeError("Already recording")

        # Validate device capabilities
        self._validate_device()

        try:
            # Clear previous data
            self._audio_data = []
            self._status_flags = []

            # Clear the queue
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break

            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                blocksize=self.chunk_size,
                device=self.device,
                callback=self._audio_callback,
                dtype=np.float32,
            )
            self._stream.start()
            self._is_recording = True
            self._is_paused = False

            device_info = self.query_device_info()
            logger.info(
                f"Started recording on device '{device_info['name']}' "
                f"at {self._sample_rate} Hz, {self._channels} channel(s)"
            )

        except sd.PortAudioError as e:
            error_msg = str(e).lower()
            if "device" in error_msg or "invalid" in error_msg:
                raise DeviceNotFoundError(f"Audio device error: {e}") from e
            raise

    def stop(self) -> None:
        """
        Stop recording audio.

        Drains any remaining audio from the queue before stopping.

        Raises:
            RuntimeError: If not currently recording.
        """
        if not self._is_recording:
            raise RuntimeError("Not recording")

        try:
            # Drain remaining audio from queue
            self._drain_queue()

            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            # Log any status issues encountered
            if self._status_flags:
                logger.warning(
                    f"Recording completed with status issues: "
                    f"{', '.join(set(self._status_flags))}"
                )

        finally:
            self._is_recording = False
            self._is_paused = False

    def pause(self) -> None:
        """
        Pause the current recording.

        Raises:
            RuntimeError: If not currently recording.
        """
        if not self._is_recording:
            raise RuntimeError("Not recording")

        self._is_paused = True
        logger.debug("Recording paused")

    def resume(self) -> None:
        """
        Resume a paused recording.

        Raises:
            RuntimeError: If not paused.
        """
        if not self._is_paused:
            raise RuntimeError("Not paused")

        self._is_paused = False
        logger.debug("Recording resumed")

    def get_volume(self) -> float:
        """
        Get the current volume level (RMS) of recorded audio.

        Drains the queue first to get the most recent audio.

        Returns:
            RMS volume level as a float between 0.0 and 1.0.

        Raises:
            RuntimeError: If not currently recording.
        """
        if not self._is_recording:
            raise RuntimeError("Not recording")

        # Drain queue to get latest audio
        self._drain_queue()

        with self._lock:
            if not self._audio_data:
                return 0.0

            all_data = np.concatenate(self._audio_data)

        if len(all_data) == 0:
            return 0.0

        rms = np.sqrt(np.mean(all_data**2))
        return float(rms)

    def get_audio_data(self) -> np.ndarray:
        """
        Get all recorded audio data.

        Drains the queue first to include all captured audio.

        Returns:
            Numpy array of recorded audio data (float32).
            Returns empty array if no data has been recorded.
        """
        # Drain queue to get all audio
        self._drain_queue()

        with self._lock:
            if not self._audio_data:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._audio_data)

    def get_status_flags(self) -> List[str]:
        """
        Get any status flags that occurred during recording.

        Returns:
            List of status flag names (e.g., 'input_overflow').
        """
        with self._lock:
            return list(self._status_flags)

    def __enter__(self) -> "AudioRecorder":
        """Enter context manager - start recording."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager - stop recording."""
        if self._is_recording:
            self.stop()
        return False

    def __del__(self) -> None:
        """Cleanup on deletion - ensure stream is closed."""
        # Check if attributes exist (may not if __init__ failed)
        if not hasattr(self, '_is_recording'):
            return
        if not hasattr(self, '_stream'):
            return
        if self._is_recording and self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass  # Ignore errors during cleanup
