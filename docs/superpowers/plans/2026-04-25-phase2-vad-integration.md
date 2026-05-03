# VAD 语音检测模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成 Silero VAD 实现实时语音活动检测，支持打断机制，延迟 < 1ms。

**Architecture:** 使用 PyTorch 加载 Silero VAD 预训练模型，实现流式音频处理。通过 asyncio 管理并发任务，支持原子性打断和状态恢复。

**Tech Stack:** Python 3.11.4, PyTorch 2.11.0, Silero VAD, asyncio, numpy

---

## 文件结构

```
O:\AII\app\references\
├── src/
│   ├── vad/
│   │   ├── __init__.py
│   │   ├── vad_monitor.py          # Silero VAD 封装
│   │   ├── audio_buffer.py         # 音频缓冲管理
│   │   └── interrupt_handler.py    # 打断处理器
│   └── utils/
│       └── audio_utils.py          # 音频预处理工具
├── tests/
│   ├── test_vad_monitor.py         # VAD 单元测试
│   ├── test_audio_buffer.py        # 缓冲测试
│   └── test_interrupt.py           # 打断测试
└── docs/
    └── vad_integration.md          # VAD 集成文档
```

---

## Task 1: 音频预处理工具

**Files:**
- Create: `src/utils/audio_utils.py`
- Test: `tests/test_audio_utils.py`

- [ ] **Step 1: Write the failing test for audio resampling**

```python
# tests/test_audio_utils.py
import pytest
import numpy as np
from src.utils.audio_utils import resample_audio


def test_resample_audio():
    """测试音频重采样"""
    # 创建测试音频：1秒的 440Hz 正弦波，采样率 44100
    duration = 1.0
    original_sr = 44100
    target_sr = 16000

    t = np.linspace(0, duration, int(original_sr * duration))
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    # 重采样
    resampled = resample_audio(audio, original_sr, target_sr)

    # 验证长度
    expected_length = int(duration * target_sr)
    assert len(resampled) == expected_length

    # 验证类型
    assert resampled.dtype == np.float32
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio_utils.py::test_resample_audio -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.utils.audio_utils'"

- [ ] **Step 3: Implement audio resampling**

```python
# src/utils/audio_utils.py
import numpy as np
from typing import Union


def resample_audio(
    audio: np.ndarray,
    original_sr: int,
    target_sr: int
) -> np.ndarray:
    """
    音频重采样

    Args:
        audio: 音频数据 (numpy array)
        original_sr: 原始采样率
        target_sr: 目标采样率

    Returns:
        重采样后的音频数据
    """
    if original_sr == target_sr:
        return audio

    # 计算重采样比例
    ratio = target_sr / original_sr

    # 使用线性插值进行重采样
    original_length = len(audio)
    target_length = int(original_length * ratio)

    # 创建原始和目标索引
    original_indices = np.arange(original_length)
    target_indices = np.linspace(0, original_length - 1, target_length)

    # 线性插值
    resampled = np.interp(target_indices, original_indices, audio)

    return resampled.astype(np.float32)


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """
    音频归一化到目标分贝

    Args:
        audio: 音频数据
        target_db: 目标分贝值

    Returns:
        归一化后的音频
    """
    # 计算当前 RMS
    rms = np.sqrt(np.mean(audio ** 2))

    if rms < 1e-10:
        return audio

    # 计算目标 RMS
    target_rms = 10 ** (target_db / 20)

    # 归一化
    normalized = audio * (target_rms / rms)

    # 防止削波
    max_val = np.max(np.abs(normalized))
    if max_val > 1.0:
        normalized = normalized / max_val

    return normalized.astype(np.float32)


def convert_to_int16(audio: np.ndarray) -> np.ndarray:
    """
    将 float32 音频转换为 int16

    Args:
        audio: float32 音频数据 [-1, 1]

    Returns:
        int16 音频数据
    """
    # 确保在 [-1, 1] 范围内
    audio = np.clip(audio, -1.0, 1.0)

    # 转换为 int16
    return (audio * 32767).astype(np.int16)


def convert_to_float32(audio: np.ndarray) -> np.ndarray:
    """
    将 int16 音频转换为 float32

    Args:
        audio: int16 音频数据

    Returns:
        float32 音频数据 [-1, 1]
    """
    return audio.astype(np.float32) / 32767.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_audio_utils.py::test_resample_audio -v`
Expected: PASS

- [ ] **Step 5: Write test for normalize_audio**

```python
# tests/test_audio_utils.py (append)
def test_normalize_audio():
    """测试音频归一化"""
    # 创建低音量音频
    audio = np.random.randn(1000).astype(np.float32) * 0.1

    # 归一化到 -20dB
    normalized = normalize_audio(audio, target_db=-20.0)

    # 验证 RMS 接近目标
    rms = np.sqrt(np.mean(normalized ** 2))
    target_rms = 10 ** (-20.0 / 20)

    assert abs(rms - target_rms) < 0.01
```

- [ ] **Step 6: Run normalize test**

Run: `pytest tests/test_audio_utils.py::test_normalize_audio -v`
Expected: PASS

- [ ] **Step 7: Commit audio utilities**

```bash
git add src/utils/audio_utils.py tests/test_audio_utils.py
git commit -m "feat: add audio preprocessing utilities"
```

---

## Task 2: 音频缓冲管理器

**Files:**
- Create: `src/vad/audio_buffer.py`
- Test: `tests/test_audio_buffer.py`

- [ ] **Step 1: Write the failing test for circular buffer**

```python
# tests/test_audio_buffer.py
import pytest
import numpy as np
from src.vad.audio_buffer import CircularAudioBuffer


def test_circular_buffer_write_read():
    """测试循环缓冲区写入和读取"""
    buffer = CircularAudioBuffer(capacity=1024, sample_rate=16000)

    # 写入数据
    data1 = np.random.randn(512).astype(np.float32)
    buffer.write(data1)

    # 读取数据
    read_data = buffer.read(512)
    assert len(read_data) == 512
    np.testing.assert_array_almost_equal(read_data, data1)


def test_circular_buffer_overwrite():
    """测试循环缓冲区覆盖"""
    buffer = CircularAudioBuffer(capacity=512, sample_rate=16000)

    # 写入超过容量的数据
    data1 = np.ones(256, dtype=np.float32)
    data2 = np.ones(256, dtype=np.float32) * 2
    data3 = np.ones(256, dtype=np.float32) * 3

    buffer.write(data1)
    buffer.write(data2)
    buffer.write(data3)  # 应该覆盖 data1

    # 读取最新数据
    read_data = buffer.read(512)
    expected = np.concatenate([data2, data3])

    np.testing.assert_array_almost_equal(read_data, expected)


def test_circular_buffer_get_latest():
    """测试获取最新数据"""
    buffer = CircularAudioBuffer(capacity=1024, sample_rate=16000)

    data1 = np.ones(512, dtype=np.float32)
    data2 = np.ones(512, dtype=np.float32) * 2

    buffer.write(data1)
    buffer.write(data2)

    # 获取最新 256 个样本
    latest = buffer.get_latest(256)
    expected = data2[-256:]

    np.testing.assert_array_almost_equal(latest, expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio_buffer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.vad.audio_buffer'"

- [ ] **Step 3: Implement circular buffer**

```python
# src/vad/audio_buffer.py
import numpy as np
from typing import Optional


class CircularAudioBuffer:
    """循环音频缓冲区"""

    def __init__(self, capacity: int, sample_rate: int = 16000):
        """
        初始化循环缓冲区

        Args:
            capacity: 缓冲区容量（样本数）
            sample_rate: 采样率
        """
        self.capacity = capacity
        self.sample_rate = sample_rate
        self.buffer = np.zeros(capacity, dtype=np.float32)
        self.write_pos = 0
        self.total_written = 0

    def write(self, data: np.ndarray):
        """
        写入音频数据

        Args:
            data: 音频数据 (float32)
        """
        data_length = len(data)

        if data_length >= self.capacity:
            # 数据长度超过容量，只保留最后 capacity 个样本
            self.buffer = data[-self.capacity:].copy()
            self.write_pos = 0
            self.total_written += data_length
        else:
            # 分段写入
            first_part = min(data_length, self.capacity - self.write_pos)
            self.buffer[self.write_pos:self.write_pos + first_part] = data[:first_part]

            remaining = data_length - first_part
            if remaining > 0:
                self.buffer[:remaining] = data[first_part:]

            self.write_pos = (self.write_pos + data_length) % self.capacity
            self.total_written += data_length

    def read(self, length: int) -> np.ndarray:
        """
        读取指定长度的数据

        Args:
            length: 要读取的长度

        Returns:
            音频数据
        """
        if length > self.total_written:
            # 请求数据超过已写入数据，返回所有可用数据
            length = self.total_written

        if length > self.capacity:
            length = self.capacity

        # 从最新数据开始读取
        start_pos = (self.write_pos - length) % self.capacity

        if start_pos + length <= self.capacity:
            # 数据连续
            return self.buffer[start_pos:start_pos + length].copy()
        else:
            # 数据跨越缓冲区边界
            first_part = self.capacity - start_pos
            second_part = length - first_part
            return np.concatenate([
                self.buffer[start_pos:],
                self.buffer[:second_part]
            ])

    def get_latest(self, length: int) -> np.ndarray:
        """
        获取最新的数据

        Args:
            length: 要获取的长度

        Returns:
            最新的音频数据
        """
        return self.read(length)

    def clear(self):
        """清空缓冲区"""
        self.buffer.fill(0)
        self.write_pos = 0
        self.total_written = 0

    def get_duration(self) -> float:
        """
        获取缓冲区中数据的时长（秒）

        Returns:
            时长
        """
        return min(self.total_written, self.capacity) / self.sample_rate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_audio_buffer.py -v`
Expected: PASS

- [ ] **Step 5: Commit audio buffer**

```bash
git add src/vad/audio_buffer.py tests/test_audio_buffer.py
git commit -m "feat: add circular audio buffer"
```

---

## Task 3: Silero VAD 集成

**Files:**
- Create: `src/vad/vad_monitor.py`
- Test: `tests/test_vad_monitor.py`

- [ ] **Step 1: Write the failing test for VAD initialization**

```python
# tests/test_vad_monitor.py
import pytest
import numpy as np
from src.vad.vad_monitor import VADMonitor


def test_vad_monitor_initialization():
    """测试 VAD 监控器初始化"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    assert monitor.sample_rate == 16000
    assert monitor.threshold == 0.5
    assert monitor.model is not None


def test_vad_detect_silence():
    """测试静音检测"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成静音（低幅度噪声）
    silence = np.random.randn(512).astype(np.float32) * 0.001

    is_speech = monitor.detect_speech(silence)

    # 静音应该不被检测为语音
    assert is_speech is False


def test_vad_detect_speech():
    """测试语音检测"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成模拟语音（高幅度正弦波）
    t = np.linspace(0, 0.032, 512)  # 32ms @ 16kHz
    speech = (np.sin(2 * np.pi * 440 * t) * 0.8).astype(np.float32)

    is_speech = monitor.detect_speech(speech)

    # 高幅度信号应该被检测为语音
    assert is_speech is True


def test_vad_get_speech_probability():
    """测试获取语音概率"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成测试音频
    audio = np.random.randn(512).astype(np.float32) * 0.5

    prob = monitor.get_speech_probability(audio)

    # 概率应该在 [0, 1] 范围内
    assert 0.0 <= prob <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vad_monitor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.vad.vad_monitor'"

- [ ] **Step 3: Implement VAD monitor**

```python
# src/vad/vad_monitor.py
import torch
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VADMonitor:
    """Silero VAD 监控器"""

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        model_name: str = "silero_vad"
    ):
        """
        初始化 VAD 监控器

        Args:
            sample_rate: 采样率（支持 8000 或 16000）
            threshold: 语音检测阈值 [0, 1]
            model_name: 模型名称
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model_name = model_name

        # 验证采样率
        if sample_rate not in [8000, 16000]:
            raise ValueError("Sample rate must be 8000 or 16000")

        # 加载模型
        self.model, self.utils = self._load_model()
        logger.info(f"VAD model loaded: {model_name}")

    def _load_model(self):
        """加载 Silero VAD 模型"""
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model=self.model_name,
                force_reload=False,
                onnx=False
            )
            model.eval()
            return model, utils
        except Exception as e:
            logger.error(f"Failed to load VAD model: {e}")
            raise

    def detect_speech(self, audio: np.ndarray) -> bool:
        """
        检测音频是否包含语音

        Args:
            audio: 音频数据 (float32, [-1, 1])

        Returns:
            是否包含语音
        """
        prob = self.get_speech_probability(audio)
        return prob > self.threshold

    def get_speech_probability(self, audio: np.ndarray) -> float:
        """
        获取语音概率

        Args:
            audio: 音频数据 (float32, [-1, 1])

        Returns:
            语音概率 [0, 1]
        """
        # 转换为 PyTorch tensor
        audio_tensor = torch.from_numpy(audio)

        # 获取语音概率
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, self.sample_rate).item()

        return speech_prob

    def reset(self):
        """重置模型状态"""
        self.model.reset_states()

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'model'):
            del self.model
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vad_monitor.py -v`
Expected: PASS (may take time to download model on first run)

- [ ] **Step 5: Commit VAD monitor**

```bash
git add src/vad/vad_monitor.py tests/test_vad_monitor.py
git commit -m "feat: integrate Silero VAD for speech detection"
```

---

## Task 4: 打断处理器

**Files:**
- Create: `src/vad/interrupt_handler.py`
- Test: `tests/test_interrupt.py`

- [ ] **Step 1: Write the failing test for interrupt handler**

```python
# tests/test_interrupt.py
import pytest
import asyncio
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException


@pytest.mark.asyncio
async def test_interrupt_handler_creation():
    """测试打断处理器创建"""
    handler = InterruptHandler()
    assert handler.is_interrupted() is False


@pytest.mark.asyncio
async def test_trigger_interrupt():
    """测试触发打断"""
    handler = InterruptHandler()

    handler.trigger_interrupt()
    assert handler.is_interrupted() is True


@pytest.mark.asyncio
async def test_clear_interrupt():
    """测试清除打断"""
    handler = InterruptHandler()

    handler.trigger_interrupt()
    handler.clear_interrupt()
    assert handler.is_interrupted() is False


@pytest.mark.asyncio
async def test_check_and_raise():
    """测试检查并抛出异常"""
    handler = InterruptHandler()

    # 未打断时不应抛出异常
    await handler.check_and_raise()

    # 打断时应抛出异常
    handler.trigger_interrupt()
    with pytest.raises(VADInterruptException):
        await handler.check_and_raise()


@pytest.mark.asyncio
async def test_with_interrupt_context():
    """测试打断上下文管理器"""
    handler = InterruptHandler()

    async with handler.interrupt_context():
        assert handler.is_interrupted() is False
        # 模拟打断
        handler.trigger_interrupt()

    # 退出上下文后应清除打断
    assert handler.is_interrupted() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_interrupt.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.vad.interrupt_handler'"

- [ ] **Step 3: Implement interrupt handler**

```python
# src/vad/interrupt_handler.py
import asyncio
from contextlib import asynccontextmanager
from typing import Optional


class VADInterruptException(Exception):
    """VAD 打断异常"""
    pass


class InterruptHandler:
    """打断处理器"""

    def __init__(self):
        """初始化打断处理器"""
        self._interrupted = False
        self._lock = asyncio.Lock()

    def is_interrupted(self) -> bool:
        """
        检查是否被打断

        Returns:
            是否被打断
        """
        return self._interrupted

    def trigger_interrupt(self):
        """触发打断"""
        self._interrupted = True

    def clear_interrupt(self):
        """清除打断状态"""
        self._interrupted = False

    async def check_and_raise(self):
        """
        检查打断状态，如果被打断则抛出异常

        Raises:
            VADInterruptException: 如果被打断
        """
        async with self._lock:
            if self._interrupted:
                raise VADInterruptException("User interrupted")

    @asynccontextmanager
    async def interrupt_context(self):
        """
        打断上下文管理器

        用法:
            async with handler.interrupt_context():
                # 执行任务
                await some_task()
        """
        try:
            self.clear_interrupt()
            yield self
        finally:
            self.clear_interrupt()

    async def cancel_task(self, task: Optional[asyncio.Task]):
        """
        取消任务

        Args:
            task: 要取消的任务
        """
        if task is None or task.done():
            return

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_interrupt.py -v`
Expected: PASS

- [ ] **Step 5: Commit interrupt handler**

```bash
git add src/vad/interrupt_handler.py tests/test_interrupt.py
git commit -m "feat: add interrupt handler for VAD"
```

---

## Task 5: 集成到 WebSocket 服务

**Files:**
- Modify: `src/server.py`
- Test: `tests/test_websocket_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_websocket_integration.py
import pytest
from fastapi.testclient import TestClient
from src.server import app
import numpy as np
import base64


client = TestClient(app)


def test_websocket_vad_integration():
    """测试 WebSocket 与 VAD 集成"""
    with client.websocket_connect("/ws/test-vad") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送静音音频
        silence = np.random.randn(512).astype(np.float32) * 0.001
        silence_bytes = (silence * 32767).astype(np.int16).tobytes()
        websocket.send_bytes(silence_bytes)

        # 接收 VAD 状态
        response = websocket.receive_json()
        assert response["type"] == "vad_status"
        assert response["is_speech"] is False


def test_websocket_interrupt():
    """测试打断功能"""
    with client.websocket_connect("/ws/test-interrupt") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送文本输入
        websocket.send_json({
            "type": "text_input",
            "content": "测试打断",
            "session_id": "test-interrupt"
        })

        # 等待处理开始
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 发送打断控制
        websocket.send_json({
            "type": "control",
            "action": "interrupt",
            "session_id": "test-interrupt"
        })

        # 接收状态更新
        status = websocket.receive_json()
        assert status["status"] == "listening"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_websocket_integration.py -v`
Expected: FAIL (VAD not integrated yet)

- [ ] **Step 3: Integrate VAD into server**

```python
# src/server.py (modify handle_audio_input function)
from vad.vad_monitor import VADMonitor
from vad.interrupt_handler import InterruptHandler, VADInterruptException

# 全局 VAD 监控器
vad_monitor = VADMonitor(sample_rate=16000, threshold=0.5)

# 会话打断处理器
interrupt_handlers = {}


async def handle_audio_input(session_id: str, audio_data: bytes):
    """处理音频输入"""
    # 更新统计
    state = manager.get_session_state(session_id)
    if state:
        state.total_audio_received += len(audio_data)

    # 转换音频格式
    import numpy as np
    audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32767.0

    # VAD 检测
    is_speech = vad_monitor.detect_speech(audio_float32)

    # 发送 VAD 状态
    await manager.send_json(session_id, {
        "type": "vad_status",
        "is_speech": is_speech,
        "timestamp": time.time()
    })

    # 如果检测到语音，触发打断
    if is_speech:
        if session_id in interrupt_handlers:
            interrupt_handlers[session_id].trigger_interrupt()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_websocket_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit integration**

```bash
git add src/server.py tests/test_websocket_integration.py
git commit -m "feat: integrate VAD into WebSocket server"
```

---

## Task 6: 性能测试

**Files:**
- Create: `tests/test_vad_performance.py`

- [ ] **Step 1: Write performance test**

```python
# tests/test_vad_performance.py
import pytest
import numpy as np
import time
from src.vad.vad_monitor import VADMonitor


def test_vad_latency():
    """测试 VAD 延迟"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成测试音频
    audio = np.random.randn(512).astype(np.float32)

    # 预热
    for _ in range(10):
        monitor.detect_speech(audio)

    # 测试延迟
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        monitor.detect_speech(audio)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms

    avg_latency = np.mean(latencies)
    max_latency = np.max(latencies)

    print(f"\nVAD Latency:")
    print(f"  Average: {avg_latency:.3f} ms")
    print(f"  Max: {max_latency:.3f} ms")
    print(f"  Min: {np.min(latencies):.3f} ms")

    # 验证延迟 < 1ms
    assert avg_latency < 1.0, f"Average latency {avg_latency}ms exceeds 1ms"
    assert max_latency < 2.0, f"Max latency {max_latency}ms exceeds 2ms"


def test_vad_throughput():
    """测试 VAD 吞吐量"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成 1 秒音频
    audio = np.random.randn(16000).astype(np.float32)

    # 测试吞吐量
    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        monitor.detect_speech(audio)
    end = time.perf_counter()

    total_time = end - start
    throughput = iterations / total_time

    print(f"\nVAD Throughput:")
    print(f"  {throughput:.2f} calls/second")
    print(f"  {throughput * 16000 / 1000:.2f} kSamples/second")

    # 验证吞吐量
    assert throughput > 100, "Throughput too low"
```

- [ ] **Step 2: Run performance test**

Run: `pytest tests/test_vad_performance.py -v -s`
Expected: PASS with performance metrics printed

- [ ] **Step 3: Commit performance tests**

```bash
git add tests/test_vad_performance.py
git commit -m "test: add VAD performance tests"
```

---

## 验收标准

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 性能测试通过（延迟 < 1ms）
- [ ] 代码覆盖率 > 80%
- [ ] 文档完整

---

## 下一步

完成阶段2后，继续：

- **阶段3**: TTS 流式合成模块（Edge TTS）
- **阶段4**: LLM 流式生成模块（Claude API）
- **阶段5**: 状态管理 + 导演指令模块
- **阶段6**: 集成测试 + 性能优化

---

**文档版本**: v1.0
**最后更新**: 2026-04-25
**作者**: Claude Sonnet 4.6
