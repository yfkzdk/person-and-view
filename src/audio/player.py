"""
AudioPlayer - Audio playback with sounddevice

Refactored with best practices from python-sounddevice reference project.
"""
import logging
import queue
import threading
from typing import Optional, Union, Dict, Any
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)


class AudioPlayerError(Exception):
    """Base exception for AudioPlayer errors."""
    pass


class DeviceNotFoundError(AudioPlayerError):
    """Raised when the specified audio device is not found."""
    pass


class DeviceIncompatibleError(AudioPlayerError):
    """Raised when the device doesn't support required capabilities."""
    pass


class AudioPlayer:
    """
    Audio player using sounddevice for real-time playback.

    Supports playback from numpy arrays and file paths, with volume control
    and playback state management (play, pause, resume, stop).

    Implements best practices from python-sounddevice reference:
    - Device capability validation before stream start
    - Queue-based buffering for smooth playback
    - Status flag checking in callbacks
    - Proper cleanup with context managers and __del__

    Attributes:
        sample_rate: Audio sample rate in Hz.
        channels: Number of audio channels (1=mono, 2=stereo).
        volume: Playback volume (0.0 to 1.0).
        device: Audio device index (None for default).
        buffer_size: Maximum number of chunks in the queue.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 1,
        volume: float = 1.0,
        device: Optional[int] = None,
        buffer_size: int = 20,
        blocksize: int = 2048,
    ) -> None:
        """
        Initialize the audio player.

        Args:
            sample_rate: Audio sample rate in Hz. Default is 44100.
                If 0, will auto-detect from device default.
            channels: Number of audio channels. Default is 1 (mono).
            volume: Initial volume level (0.0 to 1.0). Default is 1.0.
            device: Audio device index. None uses the default device.
            buffer_size: Maximum chunks in queue. Default is 20.
            blocksize: Audio block size in frames. Default is 2048.

        Raises:
            ValueError: If sample_rate or channels is invalid.
        """
        if sample_rate < 0:
            raise ValueError(f"sample_rate must be non-negative, got {sample_rate}")
        if channels <= 0:
            raise ValueError(f"channels must be positive, got {channels}")
        if buffer_size <= 0:
            raise ValueError(f"buffer_size must be positive, got {buffer_size}")
        if blocksize <= 0:
            raise ValueError(f"blocksize must be positive, got {blocksize}")

        self._sample_rate = sample_rate
        self._channels = channels
        self._volume = 0.0
        self.volume = volume  # Use setter for clamping
        self.device = device
        self.buffer_size = buffer_size
        self.blocksize = blocksize

        self._is_playing = False
        self._is_paused = False
        self._stream: Optional[sd.OutputStream] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._audio_data: np.ndarray = np.array([], dtype=np.float32)
        self._position: int = 0
        self._lock = threading.Lock()
        self._status_flags: list = []  # Track status issues for debugging
        self._finished_event = threading.Event()

    @property
    def sample_rate(self) -> int:
        """Get the sample rate (auto-detected if was 0)."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Get the number of channels."""
        return self._channels

    @property
    def volume(self) -> float:
        """Get the current volume level."""
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        """Set the volume level, clamped to [0.0, 1.0]."""
        self._volume = max(0.0, min(1.0, float(value)))

    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        """Check if playback is paused."""
        return self._is_paused

    @staticmethod
    def get_device_list() -> list:
        """
        Get a list of all available audio output devices.

        Returns:
            List of dictionaries containing device information.
            Each dict has keys: 'index', 'name', 'max_output_channels',
            'default_samplerate', 'default_low_output_latency'.
        """
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_output_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': dev['name'],
                    'max_output_channels': dev['max_output_channels'],
                    'default_samplerate': dev['default_samplerate'],
                    'default_low_output_latency': dev['default_low_output_latency'],
                })
        return devices

    def query_device_info(self) -> Dict[str, Any]:
        """
        Query the capabilities of the configured audio device.

        Returns:
            Dictionary with device capabilities including:
            - name: Device name
            - max_output_channels: Maximum output channels
            - default_samplerate: Default sample rate
            - default_low_output_latency: Default low latency

        Raises:
            DeviceNotFoundError: If the device doesn't exist.
        """
        try:
            device_info = sd.query_devices(self.device, 'output')
            return {
                'name': device_info['name'],
                'max_output_channels': device_info['max_output_channels'],
                'default_samplerate': int(device_info['default_samplerate']),
                'default_low_output_latency': device_info['default_low_output_latency'],
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

        # Check output channels
        if device_info['max_output_channels'] < self._channels:
            raise DeviceIncompatibleError(
                f"Device '{device_info['name']}' only supports "
                f"{device_info['max_output_channels']} output channels, "
                f"but {self._channels} requested."
            )

        # Auto-detect sample rate if not specified
        if self._sample_rate == 0:
            self._sample_rate = device_info['default_samplerate']
            logger.info(
                f"Auto-detected sample rate: {self._sample_rate} Hz "
                f"for device '{device_info['name']}'"
            )

    def _audio_callback(
        self, outdata: np.ndarray, frames: int, time, status
    ) -> None:
        """
        Callback function for audio stream to output data.

        Implements best practices:
        - Checks status flags for underflow/overflow
        - Uses non-blocking queue operations
        - Logs status conditions for debugging
        - Raises CallbackStop/CallbackAbort appropriately

        Args:
            outdata: Output audio data buffer.
            frames: Number of frames.
            time: Timing information.
            status: Status flags indicating stream conditions.
        """
        # Check and log status flags
        if status:
            status_msg = []
            if status.output_underflow:
                status_msg.append("output_underflow")
            if status.output_overflow:
                status_msg.append("output_overflow")
            if status_msg:
                logger.warning(f"Audio callback status: {', '.join(status_msg)}")
                with self._lock:
                    self._status_flags.extend(status_msg)

        # Handle underflow by aborting
        if status and status.output_underflow:
            logger.error("Output underflow detected, aborting playback")
            raise sd.CallbackAbort

        if self._is_paused:
            outdata.fill(0)
            return

        # Try to get data from queue (non-blocking)
        try:
            chunk = self._audio_queue.get_nowait()
            # Apply volume
            audio_chunk = chunk * self._volume

            # Output the audio data
            if self._channels == 1:
                outdata[:len(audio_chunk), 0] = audio_chunk
                if len(audio_chunk) < frames:
                    outdata[len(audio_chunk):].fill(0)
            else:
                # For stereo, reshape if needed
                if len(audio_chunk.shape) == 1:
                    # Mono data to stereo output - duplicate
                    outdata[:len(audio_chunk)] = audio_chunk.reshape(-1, 1)
                else:
                    outdata[:len(audio_chunk)] = audio_chunk
                if len(audio_chunk) < frames:
                    outdata[len(audio_chunk):].fill(0)

        except queue.Empty:
            # Queue is empty - check if we're at end of audio
            with self._lock:
                remaining = len(self._audio_data) - self._position

            if remaining <= 0:
                # End of audio - signal completion
                logger.debug("Audio playback completed")
                self._finished_event.set()
                raise sd.CallbackStop
            else:
                # Buffer underrun - this shouldn't happen with proper pre-filling
                logger.error("Buffer underrun: queue empty but audio remains")
                raise sd.CallbackAbort

    def _fill_queue(self) -> None:
        """Fill the audio queue with chunks from the audio data."""
        chunk_size = self.blocksize
        total_frames = len(self._audio_data)

        # Pre-fill queue with 10-20 blocks
        prefill_count = min(self.buffer_size, total_frames // chunk_size + 1)

        for _ in range(prefill_count):
            start = self._position
            end = min(start + chunk_size, total_frames)

            if start >= total_frames:
                break

            chunk = self._audio_data[start:end]

            # Pad last chunk if needed
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')

            try:
                self._audio_queue.put_nowait(chunk)
            except queue.Full:
                logger.warning("Queue full during pre-fill")
                break

            with self._lock:
                self._position = end

    def _refill_worker(self) -> None:
        """Worker thread to refill the queue during playback."""
        chunk_size = self.blocksize
        total_frames = len(self._audio_data)

        while self._is_playing and not self._finished_event.is_set():
            try:
                # Check if we need to refill
                if self._audio_queue.qsize() < self.buffer_size // 2:
                    with self._lock:
                        start = self._position
                        end = min(start + chunk_size, total_frames)

                        if start >= total_frames:
                            break

                        chunk = self._audio_data[start:end]

                        # Pad last chunk if needed
                        if len(chunk) < chunk_size:
                            chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')

                        try:
                            self._audio_queue.put(chunk, timeout=0.1)
                            self._position = end
                        except queue.Full:
                            pass  # Queue is full, try again later
                else:
                    # Sleep a bit to avoid busy waiting
                    self._finished_event.wait(timeout=0.01)
            except Exception as e:
                logger.error(f"Error in refill worker: {e}")
                break

    def play(self, audio_data: np.ndarray) -> None:
        """
        Play audio from a numpy array.

        Args:
            audio_data: Audio data as numpy array (float32).

        Raises:
            RuntimeError: If already playing.
            TypeError: If audio_data is not a numpy array.
            ValueError: If audio_data is empty.
            DeviceNotFoundError: If the audio device is not found.
            DeviceIncompatibleError: If the device lacks required capabilities.
        """
        if self._is_playing:
            raise RuntimeError("Already playing")

        if not isinstance(audio_data, np.ndarray):
            raise TypeError("audio_data must be a numpy array")

        if len(audio_data) == 0:
            raise ValueError("audio_data cannot be empty")

        # Validate device capabilities
        self._validate_device()

        # Ensure float32
        self._audio_data = audio_data.astype(np.float32)
        self._position = 0
        self._status_flags = []
        self._finished_event.clear()

        # Clear the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        # Pre-fill the queue
        self._fill_queue()

        try:
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                callback=self._audio_callback,
                dtype=np.float32,
                device=self.device,
                blocksize=self.blocksize,
            )
            self._stream.start()
            self._is_playing = True
            self._is_paused = False

            device_info = self.query_device_info()
            logger.info(
                f"Started playback on device '{device_info['name']}' "
                f"at {self._sample_rate} Hz, {self._channels} channel(s)"
            )

        except sd.PortAudioError as e:
            error_msg = str(e).lower()
            if "device" in error_msg or "invalid" in error_msg:
                raise DeviceNotFoundError(f"Audio device error: {e}") from e
            raise

    def play_file(self, file_path: Union[str, Path]) -> None:
        """
        Play audio from a file.

        Loads the entire file into memory for playback. For large files,
        consider using play_file_streaming() instead.

        Args:
            file_path: Path to the audio file.

        Raises:
            RuntimeError: If already playing.
            ValueError: If the file cannot be read.
            DeviceNotFoundError: If the audio device is not found.
            DeviceIncompatibleError: If the device lacks required capabilities.
        """
        if self._is_playing:
            raise RuntimeError("Already playing")

        try:
            audio_data, sr = sf.read(str(file_path), dtype="float32")
        except Exception as e:
            raise ValueError(f"Failed to read audio file: {e}") from e

        # Update sample rate to match file
        self._sample_rate = sr
        self.play(audio_data)

    def play_file_streaming(
        self, file_path: Union[str, Path], blocksize: int = 2048
    ) -> None:
        """
        Play audio from a file using streaming (memory-efficient for large files).

        Args:
            file_path: Path to the audio file.
            blocksize: Number of frames to read per block. Default is 2048.

        Raises:
            RuntimeError: If already playing.
            ValueError: If the file cannot be read.
            DeviceNotFoundError: If the audio device is not found.
            DeviceIncompatibleError: If the device lacks required capabilities.
        """
        if self._is_playing:
            raise RuntimeError("Already playing")

        try:
            # Open the file to get metadata
            with sf.SoundFile(str(file_path)) as f:
                self._sample_rate = f.samplerate
                self._channels = f.channels

                # Validate device
                self._validate_device()

                # Read entire file for now (could be optimized for true streaming)
                audio_data = f.read(dtype='float32')

        except Exception as e:
            raise ValueError(f"Failed to read audio file: {e}") from e

        self.play(audio_data)

    def pause(self) -> None:
        """
        Pause the current playback.

        Raises:
            RuntimeError: If not currently playing.
        """
        if not self._is_playing:
            raise RuntimeError("Not playing")

        self._is_paused = True
        logger.debug("Playback paused")

    def resume(self) -> None:
        """
        Resume a paused playback.

        Raises:
            RuntimeError: If not paused.
        """
        if not self._is_paused:
            raise RuntimeError("Not paused")

        self._is_paused = False
        logger.debug("Playback resumed")

    def stop(self) -> None:
        """
        Stop the current playback.

        Raises:
            RuntimeError: If not currently playing.
        """
        if not self._is_playing:
            raise RuntimeError("Not playing")

        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            # Log any status issues encountered
            if self._status_flags:
                logger.warning(
                    f"Playback completed with status issues: "
                    f"{', '.join(set(self._status_flags))}"
                )

        finally:
            self._is_playing = False
            self._is_paused = False
            self._position = 0
            self._finished_event.set()

    def get_position(self) -> int:
        """
        Get the current playback position in frames.

        Returns:
            Current position in frames (0 when not playing).
        """
        with self._lock:
            return self._position

    def get_duration(self) -> int:
        """
        Get the total duration of the current audio in frames.

        Returns:
            Total frames in the audio (0 when not playing).
        """
        with self._lock:
            return len(self._audio_data)

    def get_status_flags(self) -> list:
        """
        Get any status flags that occurred during playback.

        Returns:
            List of status flag names (e.g., 'output_underflow').
        """
        with self._lock:
            return list(self._status_flags)

    def wait_until_finished(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until playback finishes.

        Args:
            timeout: Maximum time to wait in seconds. None waits indefinitely.

        Returns:
            True if playback finished, False if timeout expired.
        """
        return self._finished_event.wait(timeout=timeout)

    def __enter__(self) -> "AudioPlayer":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager - stop playback if active."""
        if self._is_playing:
            self.stop()
        return False

    def __del__(self) -> None:
        """Cleanup on deletion - ensure stream is closed."""
        # Check if attributes exist (may not if __init__ failed)
        if not hasattr(self, '_is_playing'):
            return
        if not hasattr(self, '_stream'):
            return
        if self._is_playing and self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass  # Ignore errors during cleanup