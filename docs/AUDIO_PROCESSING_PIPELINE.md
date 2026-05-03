# Audio Processing Pipeline Documentation

## Overview

The audio processing pipeline provides a comprehensive set of tools for real-time audio recording, playback, voice activity detection, text-to-speech synthesis, and audio feature extraction. This pipeline is designed to support the emotion-aware voice AI system with high-performance, thread-safe operations.

**Optimized with best practices from reference projects**:
- python-sounddevice-master: Device selection, queue buffering, callback patterns
- py-webrtcvad-master: Sliding window VAD algorithm with 90% threshold
- edge-tts-master: Async streaming, voice management, subtitle support
- librosa-main: Parameter validation, streaming, resampling options

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Audio Processing Pipeline                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │ AudioRecorder│──────▶│ VADDetector  │──────▶│AudioProcessor│  │
│  │  (Record)    │      │  (Detect)    │      │  (Extract)   │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                                              │         │
│         │                                              │         │
│         ▼                                              ▼         │
│  ┌──────────────┐                              ┌──────────────┐  │
│  │ AudioPlayer  │                              │   TTSEngine  │  │
│  │   (Play)     │                              │  (Synthesize)│  │
│  └──────────────┘                              └──────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Key Technology |
|-----------|---------|----------------|
| **AudioRecorder** | Real-time audio capture | sounddevice |
| **AudioPlayer** | Audio playback with controls | sounddevice, soundfile |
| **VADDetector** | Voice activity detection | webrtcvad |
| **TTSEngine** | Text-to-speech synthesis | edge-tts |
| **AudioProcessor** | Feature extraction | librosa |

---

## Components

### 1. AudioRecorder

**Purpose**: Real-time audio recording with volume detection and lifecycle control.

**Key Features**:
- Configurable sample rate, channels, and chunk size
- Recording control: start, stop, pause, resume
- Real-time volume detection (RMS calculation)
- Thread-safe audio data collection
- Context manager support for automatic cleanup

**API Reference**:

```python
class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        device: Optional[int] = None,
    ) -> None

    def start(self) -> None
    def stop(self) -> None
    def pause(self) -> None
    def resume(self) -> None
    def get_volume(self) -> float
    def get_audio_data(self) -> np.ndarray

    @property
    def is_recording(self) -> bool
    @property
    def is_paused(self) -> bool
```

**Usage Example**:

```python
from src.audio import AudioRecorder

# Basic recording
recorder = AudioRecorder(sample_rate=16000, channels=1)
recorder.start()

# Record for 5 seconds
import time
time.sleep(5)

recorder.stop()
audio_data = recorder.get_audio_data()

# Using context manager
with AudioRecorder() as recorder:
    time.sleep(3)
    volume = recorder.get_volume()
    print(f"Current volume: {volume}")
```

**Configuration Options**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | int | 16000 | Audio sample rate in Hz |
| `channels` | int | 1 | Number of audio channels (1=mono, 2=stereo) |
| `chunk_size` | int | 1024 | Samples per audio chunk |
| `device` | Optional[int] | None | Audio device index (None=default) |

**Dependencies**: `sounddevice`, `numpy`

---

### 2. AudioPlayer

**Purpose**: Audio playback from numpy arrays or files with volume control and state management.

**Key Features**:
- Play from numpy arrays or file paths
- Playback control: play, pause, resume, stop
- Volume control (0.0 to 1.0)
- Playback state queries (is_playing, is_paused, get_position, get_duration)
- Thread-safe position tracking
- Context manager support

**API Reference**:

```python
class AudioPlayer:
    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 1,
        volume: float = 1.0,
        device: Optional[int] = None,
    ) -> None

    def play(self, audio_data: np.ndarray) -> None
    def play_file(self, file_path: Union[str, Path]) -> None
    def pause(self) -> None
    def resume(self) -> None
    def stop(self) -> None
    def get_position(self) -> int
    def get_duration(self) -> int

    @property
    def volume(self) -> float
    @volume.setter
    def volume(self, value: float) -> None
    @property
    def is_playing(self) -> bool
    @property
    def is_paused(self) -> bool
```

**Usage Example**:

```python
from src.audio import AudioPlayer
import numpy as np

# Play from numpy array
player = AudioPlayer(sample_rate=44100, volume=0.8)
audio_data = np.random.randn(44100).astype(np.float32)  # 1 second of noise
player.play(audio_data)

# Play from file
player.play_file("output.mp3")

# Volume control
player.volume = 0.5  # 50% volume

# Playback control
player.pause()
player.resume()
player.stop()
```

**Configuration Options**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | int | 44100 | Audio sample rate in Hz |
| `channels` | int | 1 | Number of audio channels |
| `volume` | float | 1.0 | Initial volume (0.0-1.0) |
| `device` | Optional[int] | None | Audio device index |

**Dependencies**: `sounddevice`, `soundfile`, `numpy`

---

### 3. VADDetector

**Purpose**: Voice activity detection using WebRTC VAD algorithm.

**Key Features**:
- Aggressiveness modes (0=quality, 3=aggressive filtering)
- Frame-based speech detection
- Stream processing for continuous audio
- Speech segment extraction with timestamps
- Requires 16kHz sample rate and 16-bit PCM audio

**API Reference**:

```python
class VADDetector:
    SAMPLE_RATE = 16000
    VALID_FRAME_DURATIONS = (10, 20, 30)  # milliseconds

    def __init__(self, aggressiveness: int = 3) -> None

    def is_speech(
        self,
        frame: np.ndarray,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
    ) -> bool

    def process_stream(
        self,
        audio: np.ndarray,
        frame_duration_ms: int = 20,
    ) -> Iterator[bool]

    def get_speech_segments(
        self,
        audio: np.ndarray,
        frame_duration_ms: int = 20,
        min_silence_ms: int = 100,
    ) -> List[Tuple[float, float]]

    @property
    def aggressiveness(self) -> int
    @property
    def sample_rate(self) -> int
```

**Usage Example**:

```python
from src.audio import VADDetector
import numpy as np

# Initialize VAD
vad = VADDetector(aggressiveness=3)

# Detect speech in a frame (16-bit PCM, 16kHz, 20ms frame)
frame = np.random.randint(-32768, 32767, 320, dtype=np.int16)
is_speech = vad.is_speech(frame)
print(f"Speech detected: {is_speech}")

# Process continuous audio stream
audio = np.random.randint(-32768, 32767, 16000, dtype=np.int16)  # 1 second
for is_speech in vad.process_stream(audio):
    print("Speech" if is_speech else "Silence")

# Extract speech segments
segments = vad.get_speech_segments(audio, min_silence_ms=100)
for start, end in segments:
    print(f"Speech segment: {start:.2f}s - {end:.2f}s")
```

**Configuration Options**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `aggressiveness` | int | 3 | VAD filtering mode (0-3) |

**Frame Duration Options**: 10ms, 20ms, or 30ms

**Important Constraints**:
- Sample rate must be 16000 Hz
- Audio must be 16-bit PCM (numpy int16)
- Audio must be mono (1D array)

**Dependencies**: `webrtcvad`, `numpy`

---

### 4. TTSEngine

**Purpose**: Text-to-speech synthesis using Microsoft Edge TTS.

**Key Features**:
- Async synthesis API
- Multiple voices with locale and gender filtering
- Speech rate adjustment
- Output to MP3 file or numpy array
- Automatic MP3 to PCM conversion
- Voice caching for performance

**API Reference**:

```python
class TTSEngine:
    def __init__(
        self,
        default_voice: str = "zh-CN-XiaoxiaoNeural",
        sample_rate: int = 24000,
    ) -> None

    async def list_voices(self) -> List[Dict[str, str]]

    async def find_voices(
        self,
        locale: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> List[Dict[str, str]]

    async def synthesize_to_file(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: Optional[str] = None,
        rate: str = "+0%",
    ) -> None

    async def synthesize_to_array(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
    ) -> np.ndarray
```

**Usage Example**:

```python
from src.audio import TTSEngine
import asyncio

async def main():
    tts = TTSEngine(default_voice="zh-CN-XiaoxiaoNeural")

    # List available voices
    voices = await tts.list_voices()
    print(f"Available voices: {len(voices)}")

    # Find Chinese female voices
    chinese_female = await tts.find_voices(locale="zh-CN", gender="Female")

    # Synthesize to file
    await tts.synthesize_to_file(
        "你好，世界！",
        "output.mp3",
        rate="+0%"
    )

    # Synthesize to numpy array
    audio_data = await tts.synthesize_to_array(
        "这是一段测试文本",
        rate="+20%"  # 20% faster
    )
    print(f"Audio shape: {audio_data.shape}")

asyncio.run(main())
```

**Configuration Options**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_voice` | str | "zh-CN-XiaoxiaoNeural" | Default voice name |
| `sample_rate` | int | 24000 | Output sample rate |

**Speech Rate Format**: `"+X%"` (faster) or `"-X%"` (slower), where X is 0-100

**Common Voices**:
- `zh-CN-XiaoxiaoNeural` - Chinese female (default)
- `zh-CN-YunxiNeural` - Chinese male
- `en-US-JennyNeural` - English female
- `en-US-GuyNeural` - English male

**Dependencies**: `edge-tts`, `imageio-ffmpeg`, `soundfile`, `numpy`

---

### 5. AudioProcessor

**Purpose**: Audio feature extraction and processing using librosa.

**Key Features**:
- Load audio from file or numpy array
- Automatic resampling to target sample rate
- MFCC extraction (Mel-frequency cepstral coefficients)
- Mel spectrogram extraction
- Chroma feature extraction (12 pitch classes)
- Spectral contrast extraction
- Peak normalization
- Silence trimming
- Method chaining for fluent API

**API Reference**:

```python
class AudioProcessor:
    def __init__(
        self,
        sample_rate: int = 22050,
        n_mfcc: int = 13,
        n_mels: int = 128,
    ) -> None

    def load_file(self, file_path: str) -> "AudioProcessor"
    def load_array(self, audio_data: np.ndarray, sr: int) -> "AudioProcessor"
    def resample(self, target_sr: int) -> "AudioProcessor"
    def extract_mfcc(self) -> np.ndarray
    def extract_mel_spectrogram(self) -> np.ndarray
    def extract_chroma(self) -> np.ndarray
    def extract_spectral_contrast(self) -> np.ndarray
    def extract_all_features(self) -> dict
    def normalize(self) -> "AudioProcessor"
    def trim_silence(self, top_db: float = 20.0) -> "AudioProcessor"

    @property
    def audio(self) -> Optional[np.ndarray]
    @property
    def sr(self) -> Optional[int]
```

**Usage Example**:

```python
from src.audio import AudioProcessor

# Load and process audio
processor = AudioProcessor(sample_rate=22050, n_mfcc=13)

# Method chaining
features = (processor
    .load_file("audio.wav")
    .normalize()
    .trim_silence()
    .extract_all_features())

print(f"MFCC shape: {features['mfcc'].shape}")
print(f"Mel spectrogram shape: {features['mel_spectrogram'].shape}")
print(f"Chroma shape: {features['chroma'].shape}")
print(f"Spectral contrast shape: {features['spectral_contrast'].shape}")

# Load from numpy array
import numpy as np
audio_data = np.random.randn(22050).astype(np.float32)
processor.load_array(audio_data, sr=22050)
mfcc = processor.extract_mfcc()
```

**Configuration Options**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | int | 22050 | Target sample rate |
| `n_mfcc` | int | 13 | Number of MFCC coefficients |
| `n_mels` | int | 128 | Number of mel bands |

**Feature Dimensions**:

| Feature | Shape | Description |
|---------|-------|-------------|
| MFCC | (n_mfcc, n_frames) | Mel-frequency cepstral coefficients |
| Mel Spectrogram | (n_mels, n_frames) | Mel-scale spectrogram |
| Chroma | (12, n_frames) | 12 pitch class energies |
| Spectral Contrast | (7, n_frames) | Spectral contrast features |

**Dependencies**: `librosa`, `soundfile`, `numpy`

---

## Integration Guide

### Common Workflows

#### 1. Record → VAD → Process

```python
from src.audio import AudioRecorder, VADDetector, AudioProcessor
import time

# Record audio
recorder = AudioRecorder(sample_rate=16000, channels=1)
recorder.start()
time.sleep(5)  # Record 5 seconds
recorder.stop()
audio_float32 = recorder.get_audio_data()

# Convert to int16 for VAD
import numpy as np
audio_int16 = (audio_float32 * 32767).astype(np.int16)

# Detect speech segments
vad = VADDetector(aggressiveness=3)
segments = vad.get_speech_segments(audio_int16)

# Extract features for each segment
processor = AudioProcessor(sample_rate=16000)
for start, end in segments:
    start_sample = int(start * 16000)
    end_sample = int(end * 16000)
    segment_audio = audio_float32[start_sample:end_sample]

    processor.load_array(segment_audio, sr=16000)
    features = processor.extract_all_features()
    print(f"Segment {start:.2f}s-{end:.2f}s: MFCC shape {features['mfcc'].shape}")
```

#### 2. TTS → Play

```python
from src.audio import TTSEngine, AudioPlayer
import asyncio

async def speak(text: str):
    tts = TTSEngine()
    player = AudioPlayer(sample_rate=24000)

    # Synthesize
    audio_data = await tts.synthesize_to_array(text)

    # Play
    player.play(audio_data)

    # Wait for playback
    import time
    time.sleep(len(audio_data) / 24000)

asyncio.run(speak("你好，欢迎使用语音助手！"))
```

#### 3. Complete Pipeline

```python
from src.audio import (
    AudioRecorder, AudioPlayer, VADDetector,
    TTSEngine, AudioProcessor
)
import asyncio
import numpy as np

async def voice_assistant():
    # Initialize components
    recorder = AudioRecorder(sample_rate=16000)
    vad = VADDetector()
    processor = AudioProcessor(sample_rate=16000)
    tts = TTSEngine()
    player = AudioPlayer(sample_rate=24000)

    # Record user input
    print("Listening...")
    with recorder:
        await asyncio.sleep(3)  # Record 3 seconds

    audio_float32 = recorder.get_audio_data()
    audio_int16 = (audio_float32 * 32767).astype(np.int16)

    # Detect speech
    segments = vad.get_speech_segments(audio_int16)
    if not segments:
        print("No speech detected")
        return

    # Extract features
    processor.load_array(audio_float32, sr=16000)
    features = processor.extract_all_features()

    # Generate response (mock)
    response = "我听到了你的声音"

    # Speak response
    audio_response = await tts.synthesize_to_array(response)
    player.play(audio_response)

asyncio.run(voice_assistant())
```

### Error Handling Best Practices

```python
from src.audio import AudioRecorder, AudioPlayer
import sounddevice as sd

# Handle device errors
try:
    recorder = AudioRecorder(device=999)  # Invalid device
    recorder.start()
except ValueError as e:
    print(f"Device error: {e}")
    # Fallback to default device
    recorder = AudioRecorder()
    recorder.start()

# Handle recording state errors
recorder = AudioRecorder()
try:
    recorder.pause()  # Not recording
except RuntimeError as e:
    print(f"State error: {e}")

# Handle file errors
player = AudioPlayer()
try:
    player.play_file("nonexistent.wav")
except ValueError as e:
    print(f"File error: {e}")
```

### Performance Considerations

1. **AudioRecorder**: Use appropriate chunk_size (1024-4096) for balance between latency and CPU usage
2. **VADDetector**: Aggressiveness mode 3 is fastest but may miss quiet speech
3. **TTSEngine**: Cache voices list to avoid repeated API calls
4. **AudioProcessor**: Process segments separately to reduce memory usage
5. **Threading**: All components are thread-safe for concurrent access

---

## Testing

### Test Coverage Summary

| Component | Tests | Coverage |
|-----------|-------|----------|
| AudioRecorder | 24 | Initialization, lifecycle, volume detection, data retrieval, device handling, context manager |
| AudioPlayer | 40 | Initialization, playback lifecycle, volume control, file/array playback, state queries, error handling |
| VADDetector | 32 | Initialization, speech detection, frame validation, stream processing, segment extraction |
| TTSEngine | 25 | Initialization, voice listing, synthesis to file/array, voice validation, error handling |
| AudioProcessor | 49 | Initialization, loading, resampling, feature extraction, normalization, trimming |

### Running Tests

```bash
# Run all audio module tests
pytest tests/audio/ -v

# Run specific component tests
pytest tests/audio/test_recorder.py -v
pytest tests/audio/test_player.py -v
pytest tests/audio/test_vad_detector.py -v
pytest tests/audio/test_tts_engine.py -v
pytest tests/audio/test_processor.py -v

# Run with coverage
pytest tests/audio/ --cov=src/audio --cov-report=html
```

### Test Structure

Tests follow TDD methodology:
1. Write failing tests first
2. Implement minimum code to pass
3. Refactor while keeping tests green

Each test file includes:
- Initialization tests
- Lifecycle/state tests
- Feature/functionality tests
- Error handling tests
- Context manager tests

---

## Dependencies

### Required Packages

```txt
# requirements.txt
sounddevice>=0.4.6        # Audio I/O
soundfile>=0.12.1         # Audio file reading
webrtcvad-wheels>=2.0.10  # Voice activity detection
edge-tts>=6.1.0           # Text-to-speech
librosa>=0.10.0           # Audio feature extraction
numpy>=1.24.0             # Numerical operations
imageio-ffmpeg>=0.4.9     # FFmpeg for MP3 conversion
```

### Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# Install with development dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

### Platform-Specific Notes

**Windows**:
- sounddevice requires PortAudio DLLs (included in wheel)
- webrtcvad-wheels provides precompiled binaries

**Linux**:
- May need to install: `sudo apt-get install libportaudio2`

**macOS**:
- No additional dependencies required

---

## Troubleshooting

### Common Issues

#### 1. Audio Device Not Found

**Error**: `ValueError: Audio device error`

**Solution**:
```python
import sounddevice as sd
print(sd.query_devices())  # List available devices
# Use device index from list
recorder = AudioRecorder(device=0)
```

#### 2. VAD Sample Rate Error

**Error**: `ValueError: Sample rate must be 16000`

**Solution**: VADDetector only supports 16kHz. Resample audio first:
```python
import librosa
audio_16k = librosa.resample(audio, orig_sr=44100, target_sr=16000)
```

#### 3. VAD Frame Duration Error

**Error**: `ValueError: Frame duration must be 10, 20, or 30 ms`

**Solution**: Use correct frame size:
```python
# For 20ms frames at 16kHz: 16000 * 0.020 = 320 samples
frame_size = int(16000 * 0.020)
```

#### 4. TTS Voice Not Found

**Error**: `ValueError: Invalid voice: xxx`

**Solution**: List available voices:
```python
import asyncio
from src.audio import TTSEngine

async def check_voices():
    tts = TTSEngine()
    voices = await tts.list_voices()
    for v in voices:
        print(v['ShortName'], v['Locale'], v['Gender'])

asyncio.run(check_voices())
```

#### 5. FFmpeg Not Found

**Error**: `FileNotFoundError: ffmpeg not found`

**Solution**: Install imageio-ffmpeg:
```bash
pip install imageio-ffmpeg
```

### Performance Optimization

1. **Reduce chunk size** for lower latency (trade-off: higher CPU)
2. **Use VAD aggressiveness mode 3** for faster processing
3. **Cache TTS voices** to avoid repeated API calls
4. **Process audio in segments** to reduce memory usage
5. **Use context managers** for automatic cleanup

---

## API Quick Reference

### AudioRecorder

```python
recorder = AudioRecorder(sample_rate=16000, channels=1, chunk_size=1024)
recorder.start()
volume = recorder.get_volume()
audio_data = recorder.get_audio_data()
recorder.stop()
```

### AudioPlayer

```python
player = AudioPlayer(sample_rate=44100, volume=1.0)
player.play(audio_array)
player.play_file("audio.wav")
player.pause()
player.resume()
player.stop()
```

### VADDetector

```python
vad = VADDetector(aggressiveness=3)
is_speech = vad.is_speech(frame)
segments = vad.get_speech_segments(audio)
```

### TTSEngine

```python
tts = TTSEngine(default_voice="zh-CN-XiaoxiaoNeural")
await tts.synthesize_to_file(text, "output.mp3")
audio = await tts.synthesize_to_array(text)
```

### AudioProcessor

```python
processor = AudioProcessor(sample_rate=22050)
features = processor.load_file("audio.wav").extract_all_features()
```

---

## Version History

- **v1.0.0** (2026-04-27): Initial release with all 5 components
  - AudioRecorder with real-time recording
  - AudioPlayer with playback controls
  - VADDetector with WebRTC VAD
  - TTSEngine with edge-tts
  - AudioProcessor with librosa features

---

## License

This audio processing pipeline is part of the Voices project.
