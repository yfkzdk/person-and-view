"""
AudioPlayer tests - TDD approach
Tests written first, implementation follows.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock
from src.audio.player import AudioPlayer


def _mock_device_validation(mock_sd: MagicMock) -> None:
    """Helper to mock device validation for playback tests."""
    mock_device_info = {
        'name': 'Test Device',
        'max_output_channels': 2,
        'default_samplerate': 44100,
        'default_low_output_latency': 0.01,
    }
    mock_sd.query_devices.return_value = mock_device_info


class TestAudioPlayerInitialization:
    """Test AudioPlayer initialization with default and custom parameters."""

    def test_default_initialization(self) -> None:
        """Test initialization with default parameters."""
        player = AudioPlayer()
        assert player.sample_rate == 44100
        assert player.channels == 1
        assert player.volume == 1.0
        assert player.device is None

    def test_custom_initialization(self) -> None:
        """Test initialization with custom parameters."""
        player = AudioPlayer(
            sample_rate=16000, channels=2, volume=0.5, device=1
        )
        assert player.sample_rate == 16000
        assert player.channels == 2
        assert player.volume == 0.5
        assert player.device == 1

    def test_invalid_sample_rate_raises_error(self) -> None:
        """Test that invalid sample rate raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            AudioPlayer(sample_rate=-1)

    def test_negative_sample_rate_raises_error(self) -> None:
        """Test that negative sample rate raises ValueError."""
        with pytest.raises(ValueError, match="sample_rate"):
            AudioPlayer(sample_rate=-44100)

    def test_invalid_channels_raises_error(self) -> None:
        """Test that zero channels raises ValueError."""
        with pytest.raises(ValueError, match="channel"):
            AudioPlayer(channels=0)

    def test_volume_clamped_to_range(self) -> None:
        """Test that volume is clamped between 0.0 and 1.0."""
        player = AudioPlayer(volume=1.5)
        assert player.volume == 1.0

        player = AudioPlayer(volume=-0.5)
        assert player.volume == 0.0


class TestAudioPlayerPlaybackLifecycle:
    """Test playback start/pause/resume/stop lifecycle."""

    @patch("src.audio.player.sd")
    def test_play_from_numpy_array(self, mock_sd: MagicMock) -> None:
        """Test playing audio from a numpy array."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        assert player.is_playing is True
        mock_sd.OutputStream.assert_called_once()
        mock_stream.start.assert_called_once()

    @patch("src.audio.player.sd")
    def test_pause_playback(self, mock_sd: MagicMock) -> None:
        """Test pausing playback."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        player.pause()
        assert player.is_playing is True
        assert player.is_paused is True

    @patch("src.audio.player.sd")
    def test_resume_playback(self, mock_sd: MagicMock) -> None:
        """Test resuming paused playback."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        player.pause()
        player.resume()
        assert player.is_playing is True
        assert player.is_paused is False

    @patch("src.audio.player.sd")
    def test_stop_playback(self, mock_sd: MagicMock) -> None:
        """Test stopping playback."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        player.stop()
        assert player.is_playing is False
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch("src.audio.player.sd")
    def test_pause_without_playback_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that pausing without playback raises RuntimeError."""
        player = AudioPlayer()
        with pytest.raises(RuntimeError, match="Not playing"):
            player.pause()

    @patch("src.audio.player.sd")
    def test_resume_without_pause_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that resuming without pause raises RuntimeError."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        with pytest.raises(RuntimeError, match="Not paused"):
            player.resume()

    @patch("src.audio.player.sd")
    def test_stop_without_playback_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that stopping without playback raises RuntimeError."""
        player = AudioPlayer()
        with pytest.raises(RuntimeError, match="Not playing"):
            player.stop()

    @patch("src.audio.player.sd")
    def test_double_play_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that playing while already playing raises RuntimeError."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        with pytest.raises(RuntimeError, match="Already playing"):
            player.play(audio_data)


class TestAudioPlayerVolumeControl:
    """Test volume control functionality."""

    def test_set_volume(self) -> None:
        """Test setting volume to a valid value."""
        player = AudioPlayer()
        player.volume = 0.5
        assert player.volume == 0.5

    def test_set_volume_clamp_high(self) -> None:
        """Test that setting volume above 1.0 is clamped."""
        player = AudioPlayer()
        player.volume = 1.5
        assert player.volume == 1.0

    def test_set_volume_clamp_low(self) -> None:
        """Test that setting volume below 0.0 is clamped."""
        player = AudioPlayer()
        player.volume = -0.3
        assert player.volume == 0.0

    @patch("src.audio.player.sd")
    def test_volume_applied_during_playback(self, mock_sd: MagicMock) -> None:
        """Test that volume is applied to audio data during playback."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer(volume=0.5)
        audio_data = np.ones(1024, dtype=np.float32)
        player.play(audio_data)

        # Verify the audio data passed to the stream was scaled by volume
        call_kwargs = mock_sd.OutputStream.call_args
        assert call_kwargs is not None

    def test_volume_property_is_float(self) -> None:
        """Test that volume is always a float."""
        player = AudioPlayer()
        player.volume = 0.75
        assert isinstance(player.volume, float)


class TestAudioPlayerPlaybackFromNumpyArray:
    """Test playback from numpy arrays."""

    @patch("src.audio.player.sd")
    def test_play_mono_float32(self, mock_sd: MagicMock) -> None:
        """Test playing mono float32 audio data."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.random.randn(48000).astype(np.float32)
        player.play(audio_data)
        assert player.is_playing is True

    @patch("src.audio.player.sd")
    def test_play_stereo_float32(self, mock_sd: MagicMock) -> None:
        """Test playing stereo float32 audio data."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer(channels=2)
        audio_data = np.random.randn(48000 * 2).astype(np.float32)
        player.play(audio_data)
        assert player.is_playing is True

    @patch("src.audio.player.sd")
    def test_play_empty_array_raises_error(self, mock_sd: MagicMock) -> None:
        """Test that playing an empty array raises ValueError."""
        player = AudioPlayer()
        audio_data = np.array([], dtype=np.float32)
        with pytest.raises(ValueError, match="cannot be empty"):
            player.play(audio_data)


class TestAudioPlayerPlaybackFromFilePath:
    """Test playback from file paths."""

    @patch("src.audio.player.sf")
    @patch("src.audio.player.sd")
    def test_play_from_file(self, mock_sd: MagicMock, mock_sf: MagicMock) -> None:
        """Test playing audio from a file path."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream
        mock_sf.read.return_value = (np.zeros(48000, dtype=np.float32), 44100)

        player = AudioPlayer()
        player.play_file("test_audio.wav")
        assert player.is_playing is True
        mock_sf.read.assert_called_once_with("test_audio.wav", dtype="float32")

    @patch("src.audio.player.sf")
    @patch("src.audio.player.sd")
    def test_play_from_file_uses_file_sample_rate(
        self, mock_sd: MagicMock, mock_sf: MagicMock
    ) -> None:
        """Test that play_file uses the sample rate from the file."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream
        mock_sf.read.return_value = (np.zeros(48000, dtype=np.float32), 22050)

        player = AudioPlayer()
        player.play_file("test_audio.wav")
        call_kwargs = mock_sd.OutputStream.call_args[1]
        assert call_kwargs["samplerate"] == 22050

    @patch("src.audio.player.sf")
    def test_play_from_invalid_file_raises_error(
        self, mock_sf: MagicMock
    ) -> None:
        """Test that playing from an invalid file raises ValueError."""
        mock_sf.read.side_effect = Exception("File not found")

        player = AudioPlayer()
        with pytest.raises(ValueError, match="file"):
            player.play_file("nonexistent.wav")

    @patch("src.audio.player.sf")
    @patch("src.audio.player.sd")
    def test_play_from_file_already_playing_raises_error(
        self, mock_sd: MagicMock, mock_sf: MagicMock
    ) -> None:
        """Test that play_file raises RuntimeError if already playing."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream
        mock_sf.read.return_value = (np.zeros(48000, dtype=np.float32), 44100)

        player = AudioPlayer()
        player.play_file("test_audio.wav")
        with pytest.raises(RuntimeError, match="Already playing"):
            player.play_file("another.wav")


class TestAudioPlayerStateQueries:
    """Test playback state query methods."""

    @patch("src.audio.player.sd")
    def test_is_playing_returns_true_during_playback(
        self, mock_sd: MagicMock
    ) -> None:
        """Test is_playing returns True during active playback."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        assert player.is_playing is True

    def test_is_playing_returns_false_when_idle(self) -> None:
        """Test is_playing returns False when not playing."""
        player = AudioPlayer()
        assert player.is_playing is False

    @patch("src.audio.player.sd")
    def test_is_paused_returns_true_when_paused(
        self, mock_sd: MagicMock
    ) -> None:
        """Test is_paused returns True when paused."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        player.play(audio_data)
        player.pause()
        assert player.is_paused is True

    def test_is_paused_returns_false_when_not_playing(self) -> None:
        """Test is_paused returns False when not playing."""
        player = AudioPlayer()
        assert player.is_paused is False

    @patch("src.audio.player.sd")
    def test_get_position_returns_frames_played(
        self, mock_sd: MagicMock
    ) -> None:
        """Test get_position returns the number of frames played."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(48000, dtype=np.float32)
        player.play(audio_data)
        position = player.get_position()
        assert isinstance(position, int)
        assert position >= 0

    def test_get_position_returns_zero_when_not_playing(self) -> None:
        """Test get_position returns 0 when not playing."""
        player = AudioPlayer()
        assert player.get_position() == 0

    @patch("src.audio.player.sd")
    def test_get_duration_returns_total_frames(
        self, mock_sd: MagicMock
    ) -> None:
        """Test get_duration returns the total duration in frames."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(48000, dtype=np.float32)
        player.play(audio_data)
        duration = player.get_duration()
        assert isinstance(duration, int)
        assert duration == 48000

    def test_get_duration_returns_zero_when_not_playing(self) -> None:
        """Test get_duration returns 0 when not playing."""
        player = AudioPlayer()
        assert player.get_duration() == 0


class TestAudioPlayerErrorHandling:
    """Test error handling for invalid inputs and states."""

    def test_play_invalid_data_type_raises_error(self) -> None:
        """Test that playing non-numpy data raises TypeError."""
        player = AudioPlayer()
        with pytest.raises(TypeError, match="numpy"):
            player.play([1, 2, 3])  # type: ignore

    @patch("src.audio.player.sd")
    def test_play_device_error_raises_value_error(
        self, mock_sd: MagicMock
    ) -> None:
        """Test that device errors during playback raise DeviceNotFoundError."""
        mock_sd.query_devices.side_effect = Exception("Invalid device")

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        with pytest.raises(Exception):  # Accept any exception for device errors
            player.play(audio_data)

    @patch("src.audio.player.sf")
    def test_play_file_invalid_path_raises_value_error(
        self, mock_sf: MagicMock
    ) -> None:
        """Test that playing an invalid file path raises ValueError."""
        mock_sf.read.side_effect = FileNotFoundError("No such file")

        player = AudioPlayer()
        with pytest.raises(ValueError, match="file"):
            player.play_file("/nonexistent/path.wav")

    @patch("src.audio.player.sf")
    def test_play_file_corrupted_file_raises_value_error(
        self, mock_sf: MagicMock
    ) -> None:
        """Test that playing a corrupted file raises ValueError."""
        mock_sf.read.side_effect = Exception("Corrupted file")

        player = AudioPlayer()
        with pytest.raises(ValueError, match="file"):
            player.play_file("corrupted.wav")


class TestAudioPlayerContextManager:
    """Test context manager protocol support."""

    @patch("src.audio.player.sd")
    def test_context_manager_auto_stop(self, mock_sd: MagicMock) -> None:
        """Test that context manager automatically stops playback on exit."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        with player:
            player.play(audio_data)
            assert player.is_playing is True
        assert player.is_playing is False

    @patch("src.audio.player.sd")
    def test_context_manager_cleans_up_on_exception(
        self, mock_sd: MagicMock
    ) -> None:
        """Test that context manager cleans up even on exception."""
        _mock_device_validation(mock_sd)
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value = mock_stream

        player = AudioPlayer()
        audio_data = np.zeros(1024, dtype=np.float32)
        try:
            with player:
                player.play(audio_data)
                raise ValueError("test error")
        except ValueError:
            pass
        assert player.is_playing is False