# Audio Processing Reference Projects Analysis

This document analyzes best practices extracted from four reference projects for audio processing implementation.

---

## Table of Contents

1. [python-sounddevice](#1-python-sounddevice)
2. [py-webrtcvad](#2-py-webrtcvad)
3. [edge-tts](#3-edge-tts)
4. [librosa](#4-librosa)
5. [Summary of Best Practices](#5-summary-of-best-practices)

---

## 1. python-sounddevice

**Location**: `O:\AII\app\references\python-sounddevice-master`

### 1.1 Device Selection and Error Handling

**Pattern**: Query device capabilities before use, with fallback to defaults.

```python
# From rec_unlimited.py - Getting device default sample rate
if args.samplerate is None:
    device_info = sd.query_devices(args.device, 'input')
    args.samplerate = int(device_info['default_samplerate'])
```

**Why Important**: Different audio devices have different capabilities. Querying device info prevents runtime errors and ensures compatibility.

**Application**: Always query device capabilities before opening streams. Use `query_devices()` to get:
- `max_input_channels` / `max_output_channels`
- `default_samplerate`
- `default_low_input_latency` / `default_high_input_latency`

### 1.2 Queue-Based Buffering

**Pattern**: Use bounded queues with pre-filling for smooth playback.

```python
# From play_long_file.py
q = queue.Queue(maxsize=args.buffersize)

# Pre-fill queue before starting stream
for _ in range(args.buffersize):
    data = f.read(args.blocksize)
    if not len(data):
        break
    q.put_nowait(data)

# Callback consumes from queue
def callback(outdata, frames, time, status):
    try:
        data = q.get_nowait()
    except queue.Empty as e:
        print('Buffer is empty: increase buffersize?', file=sys.stderr)
        raise sd.CallbackAbort from e
```

**Why Important**:
- Pre-filling prevents underruns at stream start
- Bounded queue prevents memory exhaustion
- `get_nowait()` in callback avoids blocking the audio thread

**Application**: Implement pre-fill buffers (10-20 blocks) before starting audio streams.

### 1.3 Callback Patterns

**Pattern**: Use status checking and proper exception handling in callbacks.

```python
# From asyncio_coroutines.py
def callback(indata, frame_count, time_info, status):
    nonlocal idx
    if status:
        print(status)  # Log any status flags
    remainder = len(buffer) - idx
    if remainder == 0:
        loop.call_soon_threadsafe(event.set)
        raise sd.CallbackStop  # Signal end of stream
    # ... process data
```

**Key Exception Types**:
- `CallbackStop`: Normal end of stream
- `CallbackAbort`: Error condition, stop immediately

**Why Important**: Status flags indicate underflow/overflow conditions. Proper handling prevents audio glitches from propagating.

### 1.4 Stream Management with Context Managers

**Pattern**: Always use context managers for stream lifecycle.

```python
# From wire.py
with sd.Stream(device=(args.input_device, args.output_device),
               samplerate=args.samplerate, blocksize=args.blocksize,
               dtype=args.dtype, latency=args.latency,
               channels=args.channels, callback=callback):
    print('#' * 80)
    print('press Return to quit')
    print('#' * 80)
    input()
```

**Why Important**: Context managers ensure proper cleanup even on exceptions, preventing resource leaks.

### 1.5 Asyncio Integration

**Pattern**: Use `asyncio.Queue` and `call_soon_threadsafe` for thread-safe communication.

```python
# From asyncio_generators.py
async def inputstream_generator(channels=1, **kwargs):
    q_in = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(q_in.put_nowait, (indata.copy(), status))

    stream = sd.InputStream(callback=callback, channels=channels, **kwargs)
    with stream:
        while True:
            indata, status = await q_in.get()
            yield indata, status
```

**Why Important**: Audio callbacks run in separate threads. `call_soon_threadsafe` safely bridges to asyncio event loop.

### 1.6 Error Handling Best Practices

```python
# From play_stream.py
def callback(outdata, frames, time, status):
    assert frames == args.blocksize
    if status.output_underflow:
        print('Output underflow: increase blocksize?', file=sys.stderr)
        raise sd.CallbackAbort
    assert not status
    # ... process data
```

**Key Patterns**:
1. Check `status.output_underflow` / `status.input_overflow`
2. Provide actionable error messages
3. Use assertions for invariant checks
4. Raise `CallbackAbort` on unrecoverable errors

---

## 2. py-webrtcvad

**Location**: `O:\AII\app\references\py-webrtcvad-master\py-webrtcvad-master`

### 2.1 Frame Object Design

**Pattern**: Encapsulate audio frame with metadata.

```python
# From example.py
class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration
```

**Why Important**: Timestamps and duration enable:
- Accurate speech segment timing
- Synchronization with other streams
- Debugging and visualization

**Application**: Create a `Frame` dataclass with:
- `data`: Raw audio bytes
- `timestamp`: Start time in seconds
- `duration`: Frame duration in seconds

### 2.2 Frame Generator Implementation

**Pattern**: Generate fixed-duration frames from continuous audio.

```python
# From example.py
def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data."""
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)  # 2 bytes per sample
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n
```

**Key Points**:
- Frame duration must be 10, 20, or 30 ms for WebRTC VAD
- Calculate byte size: `sample_rate * duration_ms / 1000 * bytes_per_sample`
- Track timestamp incrementally

### 2.3 VAD Collector Algorithm (Sliding Window + State Machine)

**Pattern**: Use ring buffer with 90% threshold for robust speech detection.

```python
# From example.py
def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    voiced_frames = []

    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # 90% threshold for triggering
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # 90% threshold for de-triggering
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []

    # Yield remaining voiced frames
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])
```

**Why Important**:
- 90% threshold prevents false triggers from brief noise
- Ring buffer provides padding (context) before/after speech
- State machine ensures clean segment boundaries

**Application**:
- Use `collections.deque(maxlen=N)` for ring buffer
- Padding duration of 300ms (10 frames of 30ms) works well
- Track state with boolean `triggered` flag

### 2.4 Ring Buffer Implementation

```python
# Key pattern: deque with maxlen
ring_buffer = collections.deque(maxlen=num_padding_frames)

# Efficient counting
num_voiced = len([f for f, speech in ring_buffer if speech])

# Clear and collect
for f, s in ring_buffer:
    voiced_frames.append(f)
ring_buffer.clear()
```

**Why Important**: `deque` with `maxlen` automatically discards oldest entries, perfect for sliding window.

---

## 3. edge-tts

**Location**: `O:\AII\app\references\edge-tts-master\edge-tts-master`

### 3.1 Async Audio Generation

**Pattern**: Async generator for streaming audio chunks.

```python
# From communicate.py
async def stream(self) -> AsyncGenerator[TTSChunk, None]:
    for self.state["partial_text"] in self.texts:
        self.state["chunk_audio_bytes"] = 0
        try:
            async for message in self.__stream():
                yield message
        except aiohttp.ClientResponseError as e:
            if e.status != 403:
                raise
            DRM.handle_client_response_error(e)
            # Retry on 403
            async for message in self.__stream():
                yield message
```

**Why Important**:
- Async generators enable real-time streaming
- Built-in retry logic for transient errors
- State management across chunks

### 3.2 Dynamic Voice Selection

**Pattern**: Filter voices by attributes using VoicesManager.

```python
# From async_audio_gen_with_dynamic_voice_selection.py
async def amain() -> None:
    voices = await VoicesManager.create()
    voice = voices.find(Gender="Male", Language="es")
    communicate = edge_tts.Communicate(TEXT, random.choice(voice)["Name"])
    await communicate.save(OUTPUT_FILE)
```

**VoicesManager Implementation**:
```python
# From voices.py
class VoicesManager:
    def find(self, **kwargs) -> List[VoicesManagerVoice]:
        matching_voices = [
            voice for voice in self.voices
            if kwargs.items() <= voice.items()
        ]
        return matching_voices
```

**Why Important**: Flexible voice selection based on attributes enables:
- Language-specific voices
- Gender preferences
- Locale-specific accents

### 3.3 Streaming with Subtitles

**Pattern**: Process multiple chunk types in single stream.

```python
# From async_audio_streaming_with_predefined_voice_and_subtitles.py
async def amain() -> None:
    communicate = edge_tts.Communicate(TEXT, VOICE)
    submaker = edge_tts.SubMaker()
    with open(OUTPUT_FILE, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

    with open(SRT_FILE, "w", encoding="utf-8") as file:
        file.write(submaker.get_srt())
```

**SubMaker Implementation**:
```python
# From submaker.py
class SubMaker:
    def feed(self, msg: TTSChunk) -> None:
        if msg["type"] not in ("WordBoundary", "SentenceBoundary"):
            raise ValueError("Invalid message type")
        self.cues.append(
            Subtitle(
                index=len(self.cues) + 1,
                start=timedelta(microseconds=msg["offset"] / 10),
                end=timedelta(microseconds=(msg["offset"] + msg["duration"]) / 10),
                content=msg["text"],
            )
        )
```

**Why Important**: Single stream produces both audio and timing metadata, enabling synchronized playback.

### 3.4 Error Handling

**Pattern**: Custom exception hierarchy for specific error conditions.

```python
# From exceptions.py
class EdgeTTSException(Exception):
    """Base exception for the edge-tts package."""

class UnknownResponse(EdgeTTSException):
    """Raised when an unknown response is received from the server."""

class UnexpectedResponse(EdgeTTSException):
    """Raised when an unexpected response is received from the server."""

class NoAudioReceived(EdgeTTSException):
    """Raised when no audio is received from the server."""

class WebSocketError(EdgeTTSException):
    """Raised when a WebSocket error occurs."""
```

**Why Important**: Specific exceptions enable targeted error handling and user-friendly messages.

### 3.5 Text Chunking for Long Content

**Pattern**: Split text into byte-limited chunks while preserving boundaries.

```python
# From communicate.py
def split_text_by_byte_length(
    text: Union[str, bytes], byte_length: int
) -> Generator[bytes, None, None]:
    """Splits text into chunks, each not exceeding a maximum byte length."""
    if isinstance(text, str):
        text = text.encode("utf-8")

    while len(text) > byte_length:
        # Find split point at whitespace
        split_at = _find_last_newline_or_space_within_limit(text, byte_length)
        if split_at < 0:
            split_at = _find_safe_utf8_split_point(text)
        # Adjust for XML entities
        split_at = _adjust_split_point_for_xml_entity(text, split_at)

        chunk = text[:split_at].strip()
        if chunk:
            yield chunk
        text = text[split_at if split_at > 0 else 1:]

    remaining_chunk = text.strip()
    if remaining_chunk:
        yield remaining_chunk
```

**Why Important**: Handles:
- UTF-8 multi-byte characters
- XML entities (`&amp;`, etc.)
- Natural word boundaries

---

## 4. librosa

**Location**: `O:\AII\app\references\librosa-main`

### 4.1 Audio Loading and Resampling

**Pattern**: Flexible loading with automatic resampling and format detection.

```python
# From core/audio.py
def load(
    path,
    *,
    sr: Optional[float] = 22050,
    mono: bool = True,
    offset: float = 0.0,
    duration: Optional[float] = None,
    dtype: DTypeLike = np.float32,
    res_type: str = "soxr_hq",
) -> Tuple[np.ndarray, Union[int, float]]:
    # Try soundfile first, fall back to audioread
    try:
        y, sr_native = __soundfile_load(path, offset, duration, dtype)
    except sf.SoundFileRuntimeError as exc:
        if isinstance(path, (str, pathlib.PurePath)):
            y, sr_native = __audioread_load(path, offset, duration, dtype)
        else:
            raise exc

    if mono:
        y = to_mono(y)

    if sr is not None:
        y = resample(y, orig_sr=sr_native, target_sr=sr, res_type=res_type)

    return y, sr
```

**Why Important**:
- Multiple backend support (soundfile, audioread)
- Automatic resampling to target rate
- Mono conversion option
- Partial loading with offset/duration

### 4.2 Streaming for Large Files

**Pattern**: Block-based streaming for memory-efficient processing.

```python
# From core/audio.py
def stream(
    path,
    *,
    block_length: int,
    frame_length: int,
    hop_length: int,
    mono: bool = True,
    offset: float = 0.0,
    duration: Optional[float] = None,
    fill_value: Optional[float] = None,
    dtype: DTypeLike = np.float32,
) -> Generator[np.ndarray, None, None]:
    sfo = sf.SoundFile(path)
    sr = sfo.samplerate

    blocks = sfo.blocks(
        blocksize=frame_length + (block_length - 1) * hop_length,
        overlap=frame_length - hop_length,
        frames=frames,
        dtype=dtype,
        fill_value=fill_value,
    )

    for block in blocks:
        if mono:
            yield to_mono(block.T)
        else:
            yield block.T
```

**Why Important**:
- Process files larger than RAM
- Overlapping blocks for frame-based analysis
- Configurable block size for memory/efficiency tradeoff

### 4.3 Resampling Options

**Pattern**: Multiple resampling algorithms with quality/speed tradeoffs.

```python
# From core/audio.py
def resample(
    y: np.ndarray,
    *,
    orig_sr: float,
    target_sr: float,
    res_type: str = "soxr_hq",
    fix: bool = True,
    scale: bool = False,
) -> np.ndarray:
    ratio = float(target_sr) / orig_sr
    n_samples = int(np.ceil(y.shape[axis] * ratio))

    if res_type.startswith("soxr"):
        y_hat = np.apply_along_axis(
            soxr.resample,
            axis=axis,
            arr=y,
            in_rate=orig_sr,
            out_rate=target_sr,
            quality=res_type,
        )
    elif res_type == "polyphase":
        gcd = np.gcd(int(orig_sr), int(target_sr))
        y_hat = scipy.signal.resample_poly(
            y, target_sr // gcd, orig_sr // gcd, axis=axis
        )
    # ... other methods
```

**Resampling Options**:
- `soxr_hq`: High-quality (default)
- `soxr_vhq`: Very high quality
- `polyphase`: Fast for integer ratios
- `scipy`/`fft`: FFT-based

### 4.4 Exception Hierarchy

**Pattern**: Simple, focused exception classes.

```python
# From util/exceptions.py
class LibrosaError(Exception):
    """The root librosa exception class"""
    pass

class ParameterError(LibrosaError):
    """Exception class for mal-formed inputs"""
    pass
```

**Why Important**: Simple hierarchy allows catching all librosa errors or specific ones.

### 4.5 Parameter Validation

**Pattern**: Validate inputs early with clear error messages.

```python
# From core/audio.py
def stream(path, *, block_length, frame_length, hop_length, ...):
    if not util.is_positive_int(block_length):
        raise ParameterError(f"block_length={block_length} must be a positive integer")
    if not util.is_positive_int(frame_length):
        raise ParameterError(f"frame_length={frame_length} must be a positive integer")
    if not util.is_positive_int(hop_length):
        raise ParameterError(f"hop_length={hop_length} must be a positive integer")
```

**Why Important**: Early validation prevents cryptic errors downstream.

---

## 5. Summary of Best Practices

### 5.1 Audio Stream Management

| Pattern | Source | Application |
|---------|--------|-------------|
| Pre-fill buffers | sounddevice | Prevent underruns at stream start |
| Bounded queues | sounddevice | Memory-safe buffering |
| Context managers | sounddevice | Guaranteed cleanup |
| Status checking | sounddevice | Detect underflow/overflow |
| Async generators | edge-tts | Real-time streaming |

### 5.2 Voice Activity Detection

| Pattern | Source | Application |
|---------|--------|-------------|
| Frame with metadata | webrtcvad | Timing and synchronization |
| Ring buffer | webrtcvad | Sliding window analysis |
| 90% threshold | webrtcvad | Robust speech detection |
| State machine | webrtcvad | Clean segment boundaries |

### 5.3 Error Handling

| Pattern | Source | Application |
|---------|--------|-------------|
| Custom exception hierarchy | edge-tts, librosa | Specific error handling |
| Status flag checking | sounddevice | Audio stream health |
| Retry logic | edge-tts | Transient error recovery |
| Early validation | librosa | Clear error messages |

### 5.4 Data Processing

| Pattern | Source | Application |
|---------|--------|-------------|
| Block-based streaming | librosa | Memory-efficient processing |
| Multiple backend support | librosa | Format flexibility |
| Resampling options | librosa | Quality/speed tradeoff |
| UTF-8 safe chunking | edge-tts | Text boundary preservation |

### 5.5 Recommended Implementation Checklist

1. **Stream Initialization**
   - Query device capabilities
   - Pre-fill buffers (10-20 blocks)
   - Use context managers

2. **Callback Design**
   - Check status flags
   - Use non-blocking queue operations
   - Raise `CallbackStop`/`CallbackAbort` appropriately
   - Copy data if needed (avoid reference issues)

3. **VAD Integration**
   - Use 30ms frames
   - 300ms padding (10 frames)
   - 90% threshold for trigger/de-trigger
   - Track timestamps for each frame

4. **Error Handling**
   - Define custom exception hierarchy
   - Validate parameters early
   - Provide actionable error messages
   - Implement retry logic for network operations

5. **Memory Management**
   - Use streaming for large files
   - Implement block-based processing
   - Set queue size limits
   - Clean up resources in finally blocks

---

## 6. Code Templates

### 6.1 Audio Stream with Queue Buffering

```python
import queue
import sounddevice as sd

def create_audio_stream(callback, blocksize=2048, buffersize=20):
    q = queue.Queue(maxsize=buffersize)

    def audio_callback(outdata, frames, time, status):
        if status.output_underflow:
            raise sd.CallbackAbort
        try:
            data = q.get_nowait()
            outdata[:len(data)] = data
            outdata[len(data):].fill(0)
        except queue.Empty:
            raise sd.CallbackAbort

    stream = sd.OutputStream(
        blocksize=blocksize,
        callback=audio_callback,
        finished_callback=lambda: print("Stream finished")
    )
    return stream, q
```

### 6.2 VAD Frame Processor

```python
import collections
from dataclasses import dataclass

@dataclass
class AudioFrame:
    data: bytes
    timestamp: float
    duration: float

def frame_generator(audio: bytes, sample_rate: int, frame_duration_ms: int = 30):
    n = int(sample_rate * frame_duration_ms / 1000 * 2)  # 16-bit
    timestamp = 0.0
    duration = frame_duration_ms / 1000.0

    for offset in range(0, len(audio) - n, n):
        yield AudioFrame(
            data=audio[offset:offset + n],
            timestamp=timestamp,
            duration=duration
        )
        timestamp += duration

def vad_processor(frames, vad, sample_rate, padding_frames=10):
    ring_buffer = collections.deque(maxlen=padding_frames)
    triggered = False
    voiced_frames = []

    for frame in frames:
        is_speech = vad.is_speech(frame.data, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            if sum(1 for _, s in ring_buffer if s) > 0.9 * padding_frames:
                triggered = True
                voiced_frames.extend(f for f, _ in ring_buffer)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            if sum(1 for _, s in ring_buffer if not s) > 0.9 * padding_frames:
                yield voiced_frames
                voiced_frames = []
                ring_buffer.clear()
                triggered = False

    if voiced_frames:
        yield voiced_frames
```

### 6.3 Async Audio Stream Handler

```python
import asyncio
from typing import AsyncGenerator
from dataclasses import dataclass

@dataclass
class AudioChunk:
    type: str  # "audio" or "metadata"
    data: bytes = None
    offset: int = None
    duration: int = None
    text: str = None

class AudioStreamHandler:
    def __init__(self):
        self.audio_queue = asyncio.Queue()
        self.metadata_queue = asyncio.Queue()

    async def process_stream(self, stream: AsyncGenerator[AudioChunk, None]):
        async for chunk in stream:
            if chunk.type == "audio":
                await self.audio_queue.put(chunk.data)
            elif chunk.type in ("WordBoundary", "SentenceBoundary"):
                await self.metadata_queue.put({
                    "offset": chunk.offset,
                    "duration": chunk.duration,
                    "text": chunk.text
                })

    async def get_audio(self) -> bytes:
        return await self.audio_queue.get()

    async def get_metadata(self) -> dict:
        return await self.metadata_queue.get()
```

---

## 7. Integration Recommendations

### For Voice Recording System

1. **Use sounddevice patterns** for:
   - Device selection with capability checking
   - Queue-based buffering with pre-fill
   - Status monitoring in callbacks

2. **Use webrtcvad patterns** for:
   - Voice activity detection
   - Frame-based processing with timestamps
   - Sliding window with 90% threshold

3. **Use edge-tts patterns** for:
   - Async streaming architecture
   - Multi-type chunk handling (audio + metadata)
   - Custom exception hierarchy

4. **Use librosa patterns** for:
   - Audio loading with format detection
   - Resampling with quality options
   - Block-based processing for large files

---

*Document generated: 2026/04/27*
*Reference projects analyzed: python-sounddevice, py-webrtcvad, edge-tts, librosa*
