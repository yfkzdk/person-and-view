"""
AudioRecorder tests - TDD approach
Tests written first, implementation follows.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.audio.recorder import (
    AudioRecorder,
    AudioRecorderError,
    DeviceNotFoundError,
    DeviceIncompatibleError,
)


class TestAudioRecorderInitialization:
    """Test AudioRecorder initialization with default and custom parameters."""

    def test_default_initialization(self) -> None:
        """Test initialization with default parameters."""
        recorder = AudioRecorder()
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.chunk_size == 1024
        assert recorder.device is None

    def test_custom_initialization(self) -> None:
        """Test initialization with custom parameters."""
        recorder = AudioRecorder(
            sample_rate=44100, channels=2, chunk_size=2048, device=1
        )
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
        assert recorder.chunk_size == 2048
        assert recorder.device == 1

    def test_invalid_sample_rate_raises_error(self) -> None:
        """Test that invalid sample rate raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            AudioRecorder(sample_rate=-1)

    def test_negative_sample_rate_raises_error(self) -> None:
        """Test that negative sample rate raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            AudioRecorder(sample_rate=-16000)

    def test_invalid_channels_raises_error(self) -> None:
        """Test that invalid channels raises ValueError."""
        with pytest.raises(ValueError, match="channel"):
            AudioRecorder(channels=0)

    def test_invalid_chunk_size_raises_error(self) -> None:
        """Test that invalid chunk size raises ValueError."""
        with pytest.raises(ValueError, match="chunk_size"):
            AudioRecorder(chunk_size=0)


class TestAudioRecorderLifecycle:
    """Test recording start/stop/pause/resume lifecycle."""

    @patch("src.audio.recorder.sd")
    def test_start_recording(self, mock_sd: MagicMock) -> None:
        """Test starting a recording session."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        recorder.start()
        assert recorder.is_recording is True

    @patch("src.audio.recorder.sd")
    def test_stop_recording(self, mock_sd: MagicMock) -> None:
        """Test stopping a recording session."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        recorder.start()
        recorder.stop()
        assert recorder.is_recording is False

    @patch("src.audio.recorder.sd")
    def test_stop_without_start_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that stopping without starting raises RuntimeError."""
        recorder = AudioRecorder()
        with pytest.raises(RuntimeError, match="Not recording"):
            recorder.stop()

    @patch("src.audio.recorder.sd")
    def test_pause_and_resume(self, mock_sd: MagicMock) -> None:
        """Test pausing and resuming recording."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        recorder.start()
        assert recorder.is_recording is True

        recorder.pause()
        assert recorder.is_paused is True
        assert recorder.is_recording is True

        recorder.resume()
        assert recorder.is_paused is False
        assert recorder.is_recording is True

    @patch("src.audio.recorder.sd")
    def test_pause_without_recording_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that pausing without recording raises RuntimeError."""
        recorder = AudioRecorder()
        with pytest.raises(RuntimeError, match="Not recording"):
            recorder.pause()

    @patch("src.audio.recorder.sd")
    def test_resume_without_pause_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that resuming without pause raises RuntimeError."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        recorder.start()
        with pytest.raises(RuntimeError, match="Not paused"):
            recorder.resume()

    @patch("src.audio.recorder.sd")
    def test_double_start_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that starting while already recording raises RuntimeError."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        recorder.start()
        with pytest.raises(RuntimeError, match="Already recording"):
            recorder.start()


class TestAudioRecorderVolumeDetection:
    """Test volume detection during recording."""

    @patch("src.audio.recorder.sd")
    def test_volume_detection_returns_float(self, mock_sd: MagicMock) -> None:
        """Test that volume detection returns a float value."""
        recorder = AudioRecorder()

        # Simulate internal audio data
        recorder._audio_data = [np.ones(1024, dtype=np.float32) * 0.5]
        recorder._is_recording = True

        volume = recorder.get_volume()
        assert isinstance(volume, float)
        assert volume >= 0.0

    @patch("src.audio.recorder.sd")
    def test_volume_detection_silent(self, mock_sd: MagicMock) -> None:
        """Test volume detection with silent audio."""
        recorder = AudioRecorder()
        recorder._audio_data = [np.zeros(1024, dtype=np.float32)]
        recorder._is_recording = True

        volume = recorder.get_volume()
        assert volume == 0.0

    @patch("src.audio.recorder.sd")
    def test_volume_detection_loud(self, mock_sd: MagicMock) -> None:
        """Test volume detection with loud audio."""
        recorder = AudioRecorder()
        recorder._audio_data = [np.ones(1024, dtype=np.float32)]
        recorder._is_recording = True

        volume = recorder.get_volume()
        assert volume > 0.0
        assert abs(volume - 1.0) < 0.01

    def test_volume_detection_without_recording_raises_error(self) -> None:
        """Test that getting volume without recording raises RuntimeError."""
        recorder = AudioRecorder()
        with pytest.raises(RuntimeError, match="Not recording"):
            recorder.get_volume()


class TestAudioRecorderDataRetrieval:
    """Test audio data retrieval."""

    @patch("src.audio.recorder.sd")
    def test_get_audio_data_returns_numpy_array(self, mock_sd: MagicMock) -> None:
        """Test that get_audio_data returns a numpy array."""
        recorder = AudioRecorder()
        expected_data = np.random.randn(2048).astype(np.float32)
        recorder._audio_data = [expected_data[:1024], expected_data[1024:]]
        recorder._is_recording = True

        audio = recorder.get_audio_data()
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32

    @patch("src.audio.recorder.sd")
    def test_get_audio_data_concatenates_chunks(self, mock_sd: MagicMock) -> None:
        """Test that get_audio_data concatenates audio chunks."""
        recorder = AudioRecorder()
        chunk1 = np.ones(1024, dtype=np.float32)
        chunk2 = np.ones(1024, dtype=np.float32) * 2
        recorder._audio_data = [chunk1, chunk2]
        recorder._is_recording = True

        audio = recorder.get_audio_data()
        assert len(audio) == 2048
        np.testing.assert_array_equal(audio[:1024], chunk1)
        np.testing.assert_array_equal(audio[1024:], chunk2)

    def test_get_audio_data_without_recording_returns_empty(self) -> None:
        """Test that get_audio_data returns empty array when not recording."""
        recorder = AudioRecorder()
        audio = recorder.get_audio_data()
        assert isinstance(audio, np.ndarray)
        assert len(audio) == 0

    @patch("src.audio.recorder.sd")
    def test_get_audio_data_stereo(self, mock_sd: MagicMock) -> None:
        """Test that get_audio_data works with stereo audio."""
        recorder = AudioRecorder(channels=2)
        chunk = np.random.randn(2048).astype(np.float32)
        recorder._audio_data = [chunk]
        recorder._is_recording = True

        audio = recorder.get_audio_data()
        assert isinstance(audio, np.ndarray)
        assert len(audio) == 2048


class TestAudioRecorderDeviceHandling:
    """Test error handling for device issues."""

    @patch("src.audio.recorder.sd")
    def test_device_not_found_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that starting with a non-existent device raises ValueError."""
        mock_sd.query_devices.side_effect = ValueError("Invalid device")

        recorder = AudioRecorder(device=9999)
        with pytest.raises(Exception, match="device"):
            recorder.start()


class TestAudioRecorderContextManager:
    """Test context manager protocol support."""

    @patch("src.audio.recorder.sd")
    def test_context_manager_start_and_stop(self, mock_sd: MagicMock) -> None:
        """Test that context manager starts and stops recording."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        with AudioRecorder() as recorder:
            assert recorder.is_recording is True

        assert recorder.is_recording is False

    @patch("src.audio.recorder.sd")
    def test_context_manager_cleans_up_on_exception(self, mock_sd: MagicMock) -> None:
        """Test that context manager cleans up even on exception."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        try:
            with recorder:
                assert recorder.is_recording is True
                raise ValueError("test error")
        except ValueError:
            pass

        assert recorder.is_recording is False


class TestAudioRecorderNewFeatures:
    """Test new features added from sounddevice best practices."""

    def test_auto_detect_sample_rate(self) -> None:
        """Test that sample_rate=0 triggers auto-detection."""
        recorder = AudioRecorder(sample_rate=0)
        assert recorder._sample_rate == 0  # Not yet detected

    @patch("src.audio.recorder.sd")
    def test_auto_detect_sample_rate_on_start(self, mock_sd: MagicMock) -> None:
        """Test that sample rate is auto-detected when starting."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 48000.0,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder(sample_rate=0)
        recorder.start()
        assert recorder.sample_rate == 48000  # Auto-detected

    @patch("src.audio.recorder.sd")
    def test_get_device_list(self, mock_sd: MagicMock) -> None:
        """Test getting list of available input devices."""
        mock_sd.query_devices.return_value = [
            {'name': 'Device 1', 'max_input_channels': 2, 'max_output_channels': 0,
             'default_samplerate': 44100, 'default_low_input_latency': 0.01},
            {'name': 'Device 2', 'max_input_channels': 0, 'max_output_channels': 2,
             'default_samplerate': 44100, 'default_low_input_latency': 0.01},
            {'name': 'Device 3', 'max_input_channels': 1, 'max_output_channels': 1,
             'default_samplerate': 16000, 'default_low_input_latency': 0.02},
        ]

        devices = AudioRecorder.get_device_list()
        assert len(devices) == 2  # Only input devices
        assert devices[0]['name'] == 'Device 1'
        assert devices[1]['name'] == 'Device 3'

    @patch("src.audio.recorder.sd")
    def test_query_device_info(self, mock_sd: MagicMock) -> None:
        """Test querying device capabilities."""
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 44100.0,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder(device=0)
        info = recorder.query_device_info()
        assert info['name'] == 'Test Device'
        assert info['max_input_channels'] == 2
        assert info['default_samplerate'] == 44100

    @patch("src.audio.recorder.sd")
    def test_device_incompatible_channels(self, mock_sd: MagicMock) -> None:
        """Test that incompatible channel count raises error."""
        mock_sd.query_devices.return_value = {
            'name': 'Mono Device',
            'max_input_channels': 1,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder(channels=2, device=0)
        with pytest.raises(DeviceIncompatibleError, match="channel"):
            recorder.start()

    @patch("src.audio.recorder.sd")
    def test_status_flags_tracking(self, mock_sd: MagicMock) -> None:
        """Test that status flags are tracked during recording."""
        mock_sd.InputStream.return_value.__enter__ = MagicMock()
        mock_sd.InputStream.return_value.__exit__ = MagicMock(return_value=False)
        mock_sd.query_devices.return_value = {
            'name': 'Test Device',
            'max_input_channels': 2,
            'default_samplerate': 16000,
            'default_low_input_latency': 0.01,
        }

        recorder = AudioRecorder()
        recorder.start()

        # Simulate status flags
        recorder._status_flags = ['input_overflow', 'input_overflow']
        flags = recorder.get_status_flags()
        assert 'input_overflow' in flags

    @patch("src.audio.recorder.sd")
    def test_buffer_size_parameter(self, mock_sd: MagicMock) -> None:
        """Test that buffer_size parameter is accepted."""
        recorder = AudioRecorder(buffer_size=50)
        assert recorder.buffer_size == 50

    def test_invalid_buffer_size_raises_error(self) -> None:
        """Test that invalid buffer size raises ValueError."""
        with pytest.raises(ValueError, match="buffer_size"):
            AudioRecorder(buffer_size=0)

    @patch("src.audio.recorder.sd")
    def test_exception_hierarchy(self, mock_sd: MagicMock) -> None:
        """Test that custom exceptions work correctly."""
        mock_sd.query_devices.side_effect = ValueError("Device not found")

        recorder = AudioRecorder(device=999)
        with pytest.raises(DeviceNotFoundError):
            recorder.start()

        # Check inheritance
        assert issubclass(DeviceNotFoundError, AudioRecorderError)
        assert issubclass(DeviceIncompatibleError, AudioRecorderError)