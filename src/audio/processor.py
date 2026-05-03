"""
AudioProcessor - audio feature extraction using librosa.

Refactored with best practices from librosa reference project:
- Custom exception hierarchy for clear error handling
- Early parameter validation
- Block-based streaming for large files
- Multiple resampling options with quality/speed tradeoffs
- Support for partial loading with offset/duration
"""
from pathlib import Path
from typing import Generator, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================


class AudioProcessorError(Exception):
    """Base exception for AudioProcessor errors."""


class ParameterError(AudioProcessorError):
    """Raised when an invalid parameter is provided."""


class AudioLoadError(AudioProcessorError):
    """Raised when audio loading fails."""


class NoAudioLoadedError(AudioProcessorError):
    """Raised when an operation requires audio but none is loaded."""


class AudioProcessor:
    """Audio feature extraction processor using librosa.

    Provides methods for loading audio, extracting features (MFCC, mel spectrogram,
    chroma, spectral contrast), and basic audio processing (normalization, trimming).

    Attributes:
        sample_rate: Target sample rate for audio processing.
        n_mfcc: Number of MFCC coefficients to extract.
        n_mels: Number of mel bands for spectrogram.
        audio: Loaded audio data as numpy array.
        sr: Sample rate of loaded audio.
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        n_mfcc: int = 13,
        n_mels: int = 128,
    ) -> None:
        """Initialize AudioProcessor.

        Args:
            sample_rate: Target sample rate. Default is 22050 (librosa default).
            n_mfcc: Number of MFCC coefficients. Default is 13.
            n_mels: Number of mel bands. Default is 128.

        Raises:
            ParameterError: If any parameter is invalid.
        """
        # Early parameter validation (librosa pattern)
        if not isinstance(sample_rate, int) or sample_rate <= 0:
            raise ParameterError(f"sample_rate must be a positive integer, got {sample_rate}")
        if not isinstance(n_mfcc, int) or n_mfcc <= 0:
            raise ParameterError(f"n_mfcc must be a positive integer, got {n_mfcc}")
        if not isinstance(n_mels, int) or n_mels <= 0:
            raise ParameterError(f"n_mels must be a positive integer, got {n_mels}")

        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_mels = n_mels
        self.audio: Optional[np.ndarray] = None
        self.sr: Optional[int] = None

    def load_file(
        self,
        file_path: str,
        offset: float = 0.0,
        duration: Optional[float] = None,
        res_type: str = "soxr_hq",
    ) -> "AudioProcessor":
        """Load audio from file with advanced options.

        Audio is automatically resampled to the target sample rate.
        Supports partial loading with offset and duration.

        Args:
            file_path: Path to audio file.
            offset: Start reading after this time (in seconds). Default 0.0.
            duration: Only load up to this much audio (in seconds). None = entire file.
            res_type: Resampling algorithm. Options: "soxr_hq" (default), "soxr_vhq",
                     "polyphase", "fft". Higher quality = slower.

        Returns:
            Self for method chaining.

        Raises:
            FileNotFoundError: If file does not exist.
            ParameterError: If offset/duration parameters are invalid.
            AudioLoadError: If file cannot be loaded as audio.
        """
        # Parameter validation
        if offset < 0:
            raise ParameterError(f"offset must be non-negative, got {offset}")
        if duration is not None and duration <= 0:
            raise ParameterError(f"duration must be positive, got {duration}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            # Use librosa.load with advanced options (librosa pattern)
            audio, sr_native = librosa.load(
                file_path,
                sr=self.sample_rate,
                mono=True,
                offset=offset,
                duration=duration,
                res_type=res_type,
            )
            self.audio = audio.astype(np.float32)
            self.sr = self.sample_rate
        except Exception as e:
            raise AudioLoadError(f"Failed to load audio file: {file_path}") from e

        return self

    def load_array(
        self, audio_data: np.ndarray, sr: int, res_type: str = "soxr_hq"
    ) -> "AudioProcessor":
        """Load audio from numpy array with resampling.

        Args:
            audio_data: Audio data as numpy array. Can be 1D (mono) or 2D (stereo).
            sr: Sample rate of the audio data.
            res_type: Resampling algorithm. Default "soxr_hq".

        Returns:
            Self for method chaining.

        Raises:
            ParameterError: If audio_data is None or empty, or sr is invalid.
        """
        if audio_data is None:
            raise ParameterError("Audio data cannot be None")

        audio = np.asarray(audio_data)

        if audio.size == 0:
            raise ParameterError("Audio data cannot be empty")

        if not isinstance(sr, int) or sr <= 0:
            raise ParameterError(f"Sample rate must be positive integer, got {sr}")

        # Convert to float32
        audio = audio.astype(np.float32)

        # Convert stereo to mono if needed
        if audio.ndim == 2:
            audio = librosa.to_mono(audio)

        # Resample if needed with configurable quality
        if sr != self.sample_rate:
            audio = librosa.resample(
                audio, orig_sr=sr, target_sr=self.sample_rate, res_type=res_type
            )

        self.audio = audio
        self.sr = self.sample_rate

        return self

    def resample(self, target_sr: int, res_type: str = "soxr_hq") -> "AudioProcessor":
        """Resample audio to target sample rate with configurable quality.

        Args:
            target_sr: Target sample rate.
            res_type: Resampling algorithm. Default "soxr_hq".

        Returns:
            Self for method chaining.

        Raises:
            ParameterError: If target_sr is invalid.
            NoAudioLoadedError: If no audio is loaded.
        """
        if not isinstance(target_sr, int) or target_sr <= 0:
            raise ParameterError(f"target_sr must be positive integer, got {target_sr}")

        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        if target_sr != self.sr:
            self.audio = librosa.resample(
                self.audio, orig_sr=self.sr, target_sr=target_sr, res_type=res_type
            )
            self.sr = target_sr

        return self

    def extract_mfcc(self) -> np.ndarray:
        """Extract MFCC features.

        Returns:
            MFCC features as numpy array of shape (n_mfcc, n_frames).

        Raises:
            NoAudioLoadedError: If no audio is loaded.
        """
        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        mfcc = librosa.feature.mfcc(
            y=self.audio, sr=self.sr, n_mfcc=self.n_mfcc
        )
        return mfcc

    def extract_mel_spectrogram(self) -> np.ndarray:
        """Extract mel spectrogram.

        Returns:
            Mel spectrogram as numpy array of shape (n_mels, n_frames).

        Raises:
            NoAudioLoadedError: If no audio is loaded.
        """
        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        mel = librosa.feature.melspectrogram(
            y=self.audio, sr=self.sr, n_mels=self.n_mels
        )
        return mel

    def extract_chroma(self) -> np.ndarray:
        """Extract chroma features.

        Returns:
            Chroma features as numpy array of shape (12, n_frames).

        Raises:
            NoAudioLoadedError: If no audio is loaded.
        """
        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        chroma = librosa.feature.chroma_stft(y=self.audio, sr=self.sr)
        return chroma

    def extract_spectral_contrast(self) -> np.ndarray:
        """Extract spectral contrast features.

        Returns:
            Spectral contrast as numpy array of shape (n_bands+1, n_frames).

        Raises:
            NoAudioLoadedError: If no audio is loaded.
        """
        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        contrast = librosa.feature.spectral_contrast(y=self.audio, sr=self.sr)
        return contrast

    def extract_all_features(self) -> dict:
        """Extract all features as a dictionary.

        Returns:
            Dictionary with keys: 'mfcc', 'mel_spectrogram', 'chroma', 'spectral_contrast'.

        Raises:
            NoAudioLoadedError: If no audio is loaded.
        """
        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        return {
            "mfcc": self.extract_mfcc(),
            "mel_spectrogram": self.extract_mel_spectrogram(),
            "chroma": self.extract_chroma(),
            "spectral_contrast": self.extract_spectral_contrast(),
        }

    def normalize(self) -> "AudioProcessor":
        """Normalize audio using peak normalization.

        Scales audio so that the maximum absolute value is 1.0.

        Returns:
            Self for method chaining.

        Raises:
            NoAudioLoadedError: If no audio is loaded.
        """
        if self.audio is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        max_val = np.max(np.abs(self.audio))
        if max_val > 0:
            self.audio = self.audio / max_val

        return self

    def trim_silence(self, top_db: float = 20.0) -> "AudioProcessor":
        """Trim silence from beginning and end of audio.

        Args:
            top_db: The threshold (in dB) below reference to consider as silence.
                    Default is 20 dB.

        Returns:
            Self for method chaining.

        Raises:
            ParameterError: If top_db is invalid.
            NoAudioLoadedError: If no audio is loaded.
        """
        if not isinstance(top_db, (int, float)) or top_db <= 0:
            raise ParameterError(f"top_db must be positive number, got {top_db}")

        if self.audio is None or self.sr is None:
            raise NoAudioLoadedError("No audio loaded. Call load_file() or load_array() first.")

        self.audio, _ = librosa.effects.trim(self.audio, top_db=top_db)

        return self

    def stream_file(
        self,
        file_path: str,
        block_length: int = 2048,
        frame_length: int = 2048,
        hop_length: int = 512,
    ) -> Generator[np.ndarray, None, None]:
        """Stream audio file in blocks for memory-efficient processing.

        This is useful for processing large files that don't fit in memory.

        Args:
            file_path: Path to audio file.
            block_length: Number of frames per block. Default 2048.
            frame_length: Length of each analysis frame. Default 2048.
            hop_length: Number of samples between frames. Default 512.

        Yields:
            Audio blocks as numpy arrays.

        Raises:
            FileNotFoundError: If file does not exist.
            ParameterError: If block parameters are invalid.
            AudioLoadError: If file cannot be loaded.
        """
        # Parameter validation (librosa pattern)
        if not isinstance(block_length, int) or block_length <= 0:
            raise ParameterError(f"block_length must be positive integer, got {block_length}")
        if not isinstance(frame_length, int) or frame_length <= 0:
            raise ParameterError(f"frame_length must be positive integer, got {frame_length}")
        if not isinstance(hop_length, int) or hop_length <= 0:
            raise ParameterError(f"hop_length must be positive integer, got {hop_length}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            # Use librosa.stream for block-based processing (librosa pattern)
            stream = librosa.stream(
                file_path,
                block_length=block_length,
                frame_length=frame_length,
                hop_length=hop_length,
                mono=True,
                sr=self.sample_rate,
                dtype=np.float32,
            )

            for block in stream:
                yield block

        except Exception as e:
            raise AudioLoadError(f"Failed to stream audio file: {file_path}") from e