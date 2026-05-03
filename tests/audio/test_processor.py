"""Tests for AudioProcessor - audio feature extraction with librosa."""
import os
import tempfile

import numpy as np
import pytest
import soundfile as sf

from src.audio.processor import (
    AudioProcessor,
    ParameterError,
    NoAudioLoadedError,
    AudioLoadError,
)


class TestAudioProcessorInit:
    """Test AudioProcessor initialization."""

    def test_init_default_sample_rate(self):
        """Test initialization with default sample rate."""
        processor = AudioProcessor()
        assert processor.sample_rate == 22050

    def test_init_custom_sample_rate(self):
        """Test initialization with custom sample rate."""
        processor = AudioProcessor(sample_rate=16000)
        assert processor.sample_rate == 16000

    def test_init_default_n_mfcc(self):
        """Test default MFCC coefficient count is 13."""
        processor = AudioProcessor()
        assert processor.n_mfcc == 13

    def test_init_custom_n_mfcc(self):
        """Test initialization with custom MFCC count."""
        processor = AudioProcessor(n_mfcc=20)
        assert processor.n_mfcc == 20

    def test_init_default_n_mels(self):
        """Test default mel band count."""
        processor = AudioProcessor()
        assert processor.n_mels == 128

    def test_init_audio_none(self):
        """Test that audio is None after initialization."""
        processor = AudioProcessor()
        assert processor.audio is None
        assert processor.sr is None


class TestLoadAudioFromFile:
    """Test loading audio from file."""

    def test_load_wav_file(self, tmp_path):
        """Test loading a valid WAV file."""
        processor = AudioProcessor()
        audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 22050)).astype(np.float32)
        file_path = str(tmp_path / "test.wav")
        sf.write(file_path, audio_data, 22050)

        result = processor.load_file(file_path)
        assert result is not None
        assert processor.audio is not None
        assert processor.sr == 22050

    def test_load_file_returns_self(self, tmp_path):
        """Test that load_file returns the processor instance for chaining."""
        processor = AudioProcessor()
        audio_data = np.zeros(22050, dtype=np.float32)
        file_path = str(tmp_path / "test.wav")
        sf.write(file_path, audio_data, 22050)

        result = processor.load_file(file_path)
        assert result is processor

    def test_load_file_resamples_to_target_sr(self, tmp_path):
        """Test that audio is resampled to target sample rate."""
        processor = AudioProcessor(sample_rate=16000)
        audio_data = np.zeros(44100, dtype=np.float32)
        file_path = str(tmp_path / "test.wav")
        sf.write(file_path, audio_data, 44100)

        processor.load_file(file_path)
        assert processor.sr == 16000

    def test_load_file_invalid_path(self):
        """Test loading from nonexistent file raises FileNotFoundError."""
        processor = AudioProcessor()
        with pytest.raises(FileNotFoundError):
            processor.load_file("/nonexistent/path/audio.wav")

    def test_load_file_invalid_format(self, tmp_path):
        """Test loading a non-audio file raises AudioLoadError."""
        processor = AudioProcessor()
        file_path = str(tmp_path / "test.txt")
        with open(file_path, "w") as f:
            f.write("not audio")

        with pytest.raises(AudioLoadError):
            processor.load_file(file_path)


class TestLoadAudioFromArray:
    """Test loading audio from numpy array."""

    def test_load_mono_audio(self):
        """Test loading mono (1D) audio array."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        result = processor.load_array(audio_data, sr=22050)

        assert processor.audio is not None
        assert processor.sr == 22050
        assert processor.audio.ndim == 1

    def test_load_stereo_audio_converted_to_mono(self):
        """Test that stereo audio is converted to mono."""
        processor = AudioProcessor()
        audio_data = np.random.randn(2, 22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        assert processor.audio.ndim == 1

    def test_load_array_returns_self(self):
        """Test that load_array returns the processor instance."""
        processor = AudioProcessor()
        audio_data = np.zeros(22050, dtype=np.float32)
        result = processor.load_array(audio_data, sr=22050)
        assert result is processor

    def test_load_array_invalid_dtype(self):
        """Test loading non-float data is converted to float32."""
        processor = AudioProcessor()
        audio_data = np.zeros(22050, dtype=np.int16)
        processor.load_array(audio_data, sr=22050)
        assert processor.audio.dtype == np.float32

    def test_load_array_empty(self):
        """Test loading empty array raises ParameterError."""
        processor = AudioProcessor()
        with pytest.raises(ParameterError):
            processor.load_array(np.array([], dtype=np.float32), sr=22050)

    def test_load_array_none(self):
        """Test loading None raises ParameterError."""
        processor = AudioProcessor()
        with pytest.raises(ParameterError):
            processor.load_array(None, sr=22050)


class TestResampleAudio:
    """Test audio resampling."""

    def test_resample_down(self):
        """Test resampling to a lower sample rate."""
        processor = AudioProcessor()
        audio_data = np.random.randn(44100).astype(np.float32)
        processor.load_array(audio_data, sr=44100)

        processor.resample(16000)
        assert processor.sr == 16000
        assert processor.audio is not None

    def test_resample_up(self):
        """Test resampling to a higher sample rate."""
        processor = AudioProcessor()
        audio_data = np.random.randn(16000).astype(np.float32)
        processor.load_array(audio_data, sr=16000)

        processor.resample(44100)
        assert processor.sr == 44100

    def test_resample_same_rate(self):
        """Test resampling to the same rate leaves audio unchanged."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        original_audio = processor.audio.copy()
        processor.resample(22050)
        np.testing.assert_array_almost_equal(processor.audio, original_audio)

    def test_resample_no_audio_loaded(self):
        """Test resampling without loaded audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.resample(16000)


class TestExtractMFCC:
    """Test MFCC feature extraction."""

    def test_mfcc_shape(self):
        """Test MFCC output shape is (n_mfcc, n_frames)."""
        processor = AudioProcessor(n_mfcc=13)
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        mfcc = processor.extract_mfcc()
        assert mfcc.shape[0] == 13
        assert mfcc.ndim == 2

    def test_mfcc_returns_numpy_array(self):
        """Test MFCC returns a numpy array."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        mfcc = processor.extract_mfcc()
        assert isinstance(mfcc, np.ndarray)

    def test_mfcc_custom_n_mfcc(self):
        """Test MFCC with custom coefficient count."""
        processor = AudioProcessor(n_mfcc=20)
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        mfcc = processor.extract_mfcc()
        assert mfcc.shape[0] == 20

    def test_mfcc_no_audio_loaded(self):
        """Test extracting MFCC without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.extract_mfcc()


class TestExtractMelSpectrogram:
    """Test mel spectrogram extraction."""

    def test_mel_spectrogram_shape(self):
        """Test mel spectrogram output shape is (n_mels, n_frames)."""
        processor = AudioProcessor(n_mels=128)
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        mel = processor.extract_mel_spectrogram()
        assert mel.shape[0] == 128
        assert mel.ndim == 2

    def test_mel_spectrogram_returns_numpy_array(self):
        """Test mel spectrogram returns a numpy array."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        mel = processor.extract_mel_spectrogram()
        assert isinstance(mel, np.ndarray)

    def test_mel_spectrogram_values_non_negative(self):
        """Test that mel spectrogram (power) values are non-negative."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        mel = processor.extract_mel_spectrogram()
        assert np.all(mel >= 0)

    def test_mel_spectrogram_no_audio_loaded(self):
        """Test extracting mel spectrogram without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.extract_mel_spectrogram()


class TestExtractChroma:
    """Test chroma feature extraction."""

    def test_chroma_shape(self):
        """Test chroma output shape is (12, n_frames)."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        chroma = processor.extract_chroma()
        assert chroma.shape[0] == 12
        assert chroma.ndim == 2

    def test_chroma_returns_numpy_array(self):
        """Test chroma returns a numpy array."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        chroma = processor.extract_chroma()
        assert isinstance(chroma, np.ndarray)

    def test_chroma_values_between_0_and_1(self):
        """Test chroma values are in [0, 1] range."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        chroma = processor.extract_chroma()
        assert np.all(chroma >= 0)
        assert np.all(chroma <= 1)

    def test_chroma_no_audio_loaded(self):
        """Test extracting chroma without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.extract_chroma()


class TestExtractSpectralContrast:
    """Test spectral contrast extraction."""

    def test_spectral_contrast_shape(self):
        """Test spectral contrast output shape is (n_bands+1, n_frames)."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        contrast = processor.extract_spectral_contrast()
        assert contrast.ndim == 2
        assert contrast.shape[0] > 0

    def test_spectral_contrast_returns_numpy_array(self):
        """Test spectral contrast returns a numpy array."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        contrast = processor.extract_spectral_contrast()
        assert isinstance(contrast, np.ndarray)

    def test_spectral_contrast_no_audio_loaded(self):
        """Test extracting spectral contrast without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.extract_spectral_contrast()


class TestExtractAllFeatures:
    """Test extracting all features at once."""

    def test_all_features_returns_dict(self):
        """Test extract_all_features returns a dictionary."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        features = processor.extract_all_features()
        assert isinstance(features, dict)

    def test_all_features_contains_expected_keys(self):
        """Test that all expected feature keys are present."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        features = processor.extract_all_features()
        expected_keys = {"mfcc", "mel_spectrogram", "chroma", "spectral_contrast"}
        assert expected_keys == set(features.keys())

    def test_all_features_values_are_numpy_arrays(self):
        """Test that all feature values are numpy arrays."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        features = processor.extract_all_features()
        for key, value in features.items():
            assert isinstance(value, np.ndarray), f"{key} is not a numpy array"

    def test_all_features_no_audio_loaded(self):
        """Test extracting all features without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.extract_all_features()


class TestNormalizeAudio:
    """Test audio normalization."""

    def test_normalize_peak(self):
        """Test peak normalization scales audio to [-1, 1]."""
        processor = AudioProcessor()
        audio_data = np.array([0.5, -0.3, 0.8, -0.6], dtype=np.float32)
        processor.load_array(audio_data, sr=22050)

        processor.normalize()
        assert np.max(np.abs(processor.audio)) == pytest.approx(1.0)

    def test_normalize_preserves_shape(self):
        """Test normalization preserves audio length."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32)
        processor.load_array(audio_data, sr=22050)

        original_length = len(processor.audio)
        processor.normalize()
        assert len(processor.audio) == original_length

    def test_normalize_silent_audio(self):
        """Test normalizing silent (all-zero) audio does not raise."""
        processor = AudioProcessor()
        audio_data = np.zeros(22050, dtype=np.float32)
        processor.load_array(audio_data, sr=22050)

        processor.normalize()
        assert np.all(processor.audio == 0.0)

    def test_normalize_no_audio_loaded(self):
        """Test normalizing without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.normalize()


class TestTrimSilence:
    """Test silence trimming."""

    def test_trim_removes_leading_silence(self):
        """Test that leading silence is removed."""
        processor = AudioProcessor()
        silence = np.zeros(10000, dtype=np.float32)
        tone = np.ones(1000, dtype=np.float32) * 0.5
        audio_data = np.concatenate([silence, tone])
        processor.load_array(audio_data, sr=22050)

        processor.trim_silence()
        assert len(processor.audio) < len(audio_data)

    def test_trim_removes_trailing_silence(self):
        """Test that trailing silence is removed."""
        processor = AudioProcessor()
        silence = np.zeros(10000, dtype=np.float32)
        tone = np.ones(1000, dtype=np.float32) * 0.5
        audio_data = np.concatenate([tone, silence])
        processor.load_array(audio_data, sr=22050)

        processor.trim_silence()
        assert len(processor.audio) < len(audio_data)

    def test_trim_preserves_non_silent_audio(self):
        """Test that non-silent audio is preserved."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32) * 0.5
        processor.load_array(audio_data, sr=22050)

        original_length = len(processor.audio)
        processor.trim_silence()
        assert len(processor.audio) > 0

    def test_trim_returns_self(self):
        """Test that trim_silence returns the processor instance."""
        processor = AudioProcessor()
        audio_data = np.random.randn(22050).astype(np.float32) * 0.5
        processor.load_array(audio_data, sr=22050)

        result = processor.trim_silence()
        assert result is processor

    def test_trim_no_audio_loaded(self):
        """Test trimming without audio raises RuntimeError."""
        processor = AudioProcessor()
        with pytest.raises(NoAudioLoadedError):
            processor.trim_silence()