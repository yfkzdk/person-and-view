# TTS 流式合成模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成 Edge TTS 实现流式语音合成，支持导演指令控制，首字延迟 < 200ms。

**Architecture:** 使用 Edge TTS 进行流式合成，通过导演指令解析器将文本标记转换为 TTS 参数，支持实时打断和音频后处理。

**Tech Stack:** Python 3.11.4, Edge TTS 7.2.8, asyncio, pydub

---

## 文件结构

```
O:\AII\app\references\
├── src/
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── edge_tts_client.py      # Edge TTS 客户端
│   │   ├── director_parser.py      # 导演指令解析器
│   │   ├── audio_processor.py      # 音频后处理
│   │   └── tts_streamer.py         # TTS 流式管理器
│   └── models/
│       └── tts_config.py           # TTS 配置模型
├── tests/
│   ├── test_edge_tts_client.py     # Edge TTS 测试
│   ├── test_director_parser.py     # 导演指令测试
│   ├── test_audio_processor.py     # 音频处理测试
│   └── test_tts_streamer.py        # 流式管理器测试
└── docs/
    └── tts_integration.md          # TTS 集成文档
```

---

## Task 1: TTS 配置模型

**Files:**
- Create: `src/models/tts_config.py`
- Test: `tests/test_tts_config.py`

- [ ] **Step 1: Write the failing test for TTS config**

```python
# tests/test_tts_config.py
import pytest
from src.models.tts_config import TTSConfig, VoiceConfig


def test_tts_config_creation():
    """测试 TTS 配置创建"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural",
            rate=1.0,
            pitch=0
        )
    )

    assert config.voice.language == "zh-CN"
    assert config.voice.name == "XiaoxiaoNeural"
    assert config.voice.rate == 1.0
    assert config.voice.pitch == 0


def test_tts_config_to_edge_tts_params():
    """测试转换为 Edge TTS 参数"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural",
            rate=1.2,
            pitch=-5
        )
    )

    params = config.to_edge_tts_params()

    assert params["voice"] == "zh-CN-XiaoxiaoNeural"
    assert params["rate"] == "+20%"
    assert params["pitch"] == "-5Hz"


def test_voice_config_default_values():
    """测试默认值"""
    voice = VoiceConfig()

    assert voice.language == "zh-CN"
    assert voice.name == "XiaoxiaoNeural"
    assert voice.rate == 1.0
    assert voice.pitch == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tts_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models.tts_config'"

- [ ] **Step 3: Implement TTS config models**

```python
# src/models/tts_config.py
from pydantic import BaseModel, Field
from typing import Optional


class VoiceConfig(BaseModel):
    """音色配置"""
    language: str = "zh-CN"
    name: str = "XiaoxiaoNeural"
    rate: float = Field(1.0, ge=0.5, le=2.0, description="语速倍率")
    pitch: int = Field(0, ge=-50, le=50, description="音调偏移 (Hz)")

    def to_edge_tts_rate(self) -> str:
        """转换为 Edge TTS 语速格式"""
        percentage = int((self.rate - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        else:
            return f"{percentage}%"

    def to_edge_tts_pitch(self) -> str:
        """转换为 Edge TTS 音调格式"""
        if self.pitch >= 0:
            return f"+{self.pitch}Hz"
        else:
            return f"{self.pitch}Hz"


class TTSConfig(BaseModel):
    """TTS 配置"""
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    output_format: str = "audio-24khz-48kbitrate-mono-mp3"

    def to_edge_tts_params(self) -> dict:
        """转换为 Edge TTS 参数"""
        voice_name = f"{self.voice.language}-{self.voice.name}"

        return {
            "voice": voice_name,
            "rate": self.voice.to_edge_tts_rate(),
            "pitch": self.voice.to_edge_tts_pitch(),
        }


class DirectorCommand(BaseModel):
    """导演指令"""
    command: str
    value: Optional[float] = None
    position: int = 0  # 在文本中的位置
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tts_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit TTS config**

```bash
git add src/models/tts_config.py tests/test_tts_config.py
git commit -m "feat: add TTS configuration models"
```

---

## Task 2: 导演指令解析器

**Files:**
- Create: `src/tts/director_parser.py`
- Test: `tests/test_director_parser.py`

- [ ] **Step 1: Write the failing test for director parser**

```python
# tests/test_director_parser.py
import pytest
from src.tts.director_parser import DirectorParser, DirectorCommand


def test_parse_volume_command():
    """解析音量指令"""
    parser = DirectorParser()

    text = "你好[压低音量]这是一段话"
    clean_text, commands = parser.parse(text)

    assert clean_text == "你好这是一段话"
    assert len(commands) == 1
    assert commands[0].command == "volume_down"
    assert commands[0].value == 0.7


def test_parse_speed_command():
    """解析语速指令"""
    parser = DirectorParser()

    text = "[加速]快说[减速]慢说"
    clean_text, commands = parser.parse(text)

    assert clean_text == "快说慢说"
    assert len(commands) == 2
    assert commands[0].command == "speed_up"
    assert commands[0].value == 1.3
    assert commands[1].command == "speed_down"
    assert commands[1].value == 0.7


def test_parse_emotion_command():
    """解析情绪指令"""
    parser = DirectorParser()

    text = "[情绪:开心]我很高兴"
    clean_text, commands = parser.parse(text)

    assert clean_text == "我很高兴"
    assert len(commands) == 1
    assert commands[0].command == "emotion"
    assert commands[0].value == "开心"


def test_parse_pause_command():
    """解析停顿指令"""
    parser = DirectorParser()

    text = "等等[停顿2秒]继续"
    clean_text, commands = parser.parse(text)

    assert clean_text == "等等继续"
    assert len(commands) == 1
    assert commands[0].command == "pause"
    assert commands[0].value == 2.0


def test_parse_multiple_commands():
    """解析多个指令"""
    parser = DirectorParser()

    text = "[压低音量][加速]快速低声说"
    clean_text, commands = parser.parse(text)

    assert clean_text == "快速低声说"
    assert len(commands) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_director_parser.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.tts.director_parser'"

- [ ] **Step 3: Implement director parser**

```python
# src/tts/director_parser.py
import re
from typing import List, Tuple
from src.models.tts_config import DirectorCommand


class DirectorParser:
    """导演指令解析器"""

    # 指令模式定义
    DIRECTIVE_PATTERNS = {
        r'\[压低音量\]': ('volume_down', 0.7),
        r'\[提高音量\]': ('volume_up', 1.3),
        r'\[加速\]': ('speed_up', 1.3),
        r'\[减速\]': ('speed_down', 0.7),
        r'\[呼吸音\]': ('breath', 0.5),
        r'\[停顿(\d+(?:\.\d+)?)秒\]': ('pause', None),
        r'\[情绪:(\w+)\]': ('emotion', None),
    }

    def __init__(self):
        """初始化解析器"""
        self.compiled_patterns = []
        for pattern, (cmd_type, default_value) in self.DIRECTIVE_PATTERNS.items():
            self.compiled_patterns.append(
                (re.compile(pattern), cmd_type, default_value)
            )

    def parse(self, text: str) -> Tuple[str, List[DirectorCommand]]:
        """
        解析文本中的导演指令

        Args:
            text: 包含指令的文本

        Returns:
            (清理后的文本, 指令列表)
        """
        commands = []
        cleaned_text = text

        for compiled_pattern, cmd_type, default_value in self.compiled_patterns:
            matches = list(compiled_pattern.finditer(text))

            for match in matches:
                # 提取参数值
                if cmd_type == 'pause':
                    value = float(match.group(1)) if match.group(1) else default_value
                elif cmd_type == 'emotion':
                    value = match.group(1)
                else:
                    value = default_value

                # 创建指令对象
                command = DirectorCommand(
                    command=cmd_type,
                    value=value,
                    position=match.start()
                )
                commands.append(command)

                # 从文本中移除指令标记
                cleaned_text = cleaned_text.replace(match.group(0), '')

        # 按位置排序
        commands.sort(key=lambda c: c.position)

        return cleaned_text.strip(), commands

    def apply_commands_to_config(
        self,
        commands: List[DirectorCommand],
        base_config
    ):
        """
        将指令应用到 TTS 配置

        Args:
            commands: 指令列表
            base_config: 基础 TTS 配置

        Returns:
            修改后的配置
        """
        config = base_config.copy()

        for cmd in commands:
            if cmd.command == 'speed_up':
                config.voice.rate *= cmd.value
            elif cmd.command == 'speed_down':
                config.voice.rate *= cmd.value
            elif cmd.command == 'emotion':
                # 根据情绪调整音色
                config.voice.name = self._get_voice_for_emotion(cmd.value)

        # 限制范围
        config.voice.rate = max(0.5, min(2.0, config.voice.rate))

        return config

    def _get_voice_for_emotion(self, emotion: str) -> str:
        """
        根据情绪获取音色名称

        Args:
            emotion: 情绪标签

        Returns:
            音色名称
        """
        emotion_voice_map = {
            '开心': 'XiaoxiaoNeural',
            '悲伤': 'YunxiNeural',
            '愤怒': 'YunjianNeural',
            '平静': 'XiaoyiNeural',
        }

        return emotion_voice_map.get(emotion, 'XiaoxiaoNeural')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_director_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit director parser**

```bash
git add src/tts/director_parser.py tests/test_director_parser.py
git commit -m "feat: add director command parser"
```

---

## Task 3: Edge TTS 客户端

**Files:**
- Create: `src/tts/edge_tts_client.py`
- Test: `tests/test_edge_tts_client.py`

- [ ] **Step 1: Write the failing test for Edge TTS client**

```python
# tests/test_edge_tts_client.py
import pytest
import asyncio
from src.tts.edge_tts_client import EdgeTTSClient
from src.models.tts_config import TTSConfig, VoiceConfig


@pytest.mark.asyncio
async def test_edge_tts_client_creation():
    """测试 Edge TTS 客户端创建"""
    config = TTSConfig()
    client = EdgeTTSClient(config)

    assert client.config == config


@pytest.mark.asyncio
async def test_synthesize_text():
    """测试文本合成"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural"
        )
    )
    client = EdgeTTSClient(config)

    # 合成文本
    audio_chunks = []
    async for chunk in client.synthesize("你好世界"):
        audio_chunks.append(chunk)

    # 验证生成了音频数据
    assert len(audio_chunks) > 0
    assert all(len(chunk) > 0 for chunk in audio_chunks)


@pytest.mark.asyncio
async def test_synthesize_with_rate():
    """测试带语速的合成"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural",
            rate=1.5  # 1.5倍速
        )
    )
    client = EdgeTTSClient(config)

    audio_chunks = []
    async for chunk in client.synthesize("快速说话"):
        audio_chunks.append(chunk)

    assert len(audio_chunks) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_edge_tts_client.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.tts.edge_tts_client'"

- [ ] **Step 3: Implement Edge TTS client**

```python
# src/tts/edge_tts_client.py
import edge_tts
import asyncio
from typing import AsyncIterator
from src.models.tts_config import TTSConfig
import logging

logger = logging.getLogger(__name__)


class EdgeTTSClient:
    """Edge TTS 客户端"""

    def __init__(self, config: TTSConfig):
        """
        初始化 Edge TTS 客户端

        Args:
            config: TTS 配置
        """
        self.config = config

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """
        流式合成文本

        Args:
            text: 要合成的文本

        Yields:
            音频数据块 (bytes)
        """
        # 获取 Edge TTS 参数
        params = self.config.to_edge_tts_params()

        logger.info(f"Synthesizing text: {text[:50]}...")
        logger.debug(f"TTS params: {params}")

        try:
            # 创建 Communicate 对象
            communicate = edge_tts.Communicate(
                text,
                **params
            )

            # 流式生成音频
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    async def synthesize_to_file(self, text: str, output_path: str):
        """
        合成文本到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
        """
        params = self.config.to_edge_tts_params()

        communicate = edge_tts.Communicate(text, **params)
        await communicate.save(output_path)

        logger.info(f"Audio saved to {output_path}")

    @staticmethod
    async def list_voices(language: str = "zh-CN"):
        """
        列出可用音色

        Args:
            language: 语言代码

        Returns:
            音色列表
        """
        voices = await edge_tts.list_voices()

        # 过滤指定语言
        filtered_voices = [
            v for v in voices
            if v["Locale"].startswith(language)
        ]

        return filtered_voices
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_edge_tts_client.py -v`
Expected: PASS (may take time to download audio on first run)

- [ ] **Step 5: Commit Edge TTS client**

```bash
git add src/tts/edge_tts_client.py tests/test_edge_tts_client.py
git commit -m "feat: add Edge TTS client with streaming support"
```

---

## Task 4: 音频后处理器

**Files:**
- Create: `src/tts/audio_processor.py`
- Test: `tests/test_audio_processor.py`

- [ ] **Step 1: Write the failing test for audio processor**

```python
# tests/test_audio_processor.py
import pytest
import numpy as np
from src.tts.audio_processor import AudioProcessor


def test_adjust_volume():
    """测试音量调节"""
    processor = AudioProcessor()

    # 创建测试音频
    audio = np.random.randn(1000).astype(np.float32) * 0.5

    # 降低音量
    adjusted = processor.adjust_volume(audio, 0.5)

    # 验证音量降低
    assert np.max(np.abs(adjusted)) < np.max(np.abs(audio))


def test_concatenate_audio():
    """测试音频拼接"""
    processor = AudioProcessor()

    # 创建两个音频块
    audio1 = np.ones(500, dtype=np.float32)
    audio2 = np.ones(500, dtype=np.float32) * 2

    # 拼接
    concatenated = processor.concatenate([audio1, audio2])

    assert len(concatenated) == 1000
    assert concatenated[0] == 1.0
    assert concatenated[500] == 2.0


def test_add_silence():
    """测试添加静音"""
    processor = AudioProcessor()

    audio = np.ones(1000, dtype=np.float32)

    # 在开头添加 0.5 秒静音
    with_silence = processor.add_silence(audio, duration_seconds=0.5, sample_rate=16000, position='start')

    # 验证长度增加
    expected_length = 1000 + int(0.5 * 16000)
    assert len(with_silence) == expected_length

    # 验证开头是静音
    assert np.all(with_silence[:int(0.5 * 16000)] == 0)


def test_apply_eq():
    """测试 EQ 均衡器"""
    processor = AudioProcessor()

    # 创建测试音频
    audio = np.random.randn(16000).astype(np.float32)

    # 应用 EQ
    eq_settings = {
        'low_shelf': 3.0,
        'mid': -1.0,
        'high_shelf': 2.0
    }

    processed = processor.apply_eq(audio, eq_settings, sample_rate=16000)

    # 验证音频被处理
    assert len(processed) == len(audio)
    assert not np.array_equal(processed, audio)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio_processor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.tts.audio_processor'"

- [ ] **Step 3: Implement audio processor**

```python
# src/tts/audio_processor.py
import numpy as np
from typing import List, Dict, Optional
from scipy import signal
import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    """音频后处理器"""

    def adjust_volume(self, audio: np.ndarray, factor: float) -> np.ndarray:
        """
        调整音量

        Args:
            audio: 音频数据
            factor: 音量因子 (0.0-2.0)

        Returns:
            调整后的音频
        """
        adjusted = audio * factor

        # 防止削波
        max_val = np.max(np.abs(adjusted))
        if max_val > 1.0:
            adjusted = adjusted / max_val

        return adjusted.astype(np.float32)

    def concatenate(self, audio_chunks: List[np.ndarray]) -> np.ndarray:
        """
        拼接音频块

        Args:
            audio_chunks: 音频块列表

        Returns:
            拼接后的音频
        """
        if not audio_chunks:
            return np.array([], dtype=np.float32)

        return np.concatenate(audio_chunks)

    def add_silence(
        self,
        audio: np.ndarray,
        duration_seconds: float,
        sample_rate: int,
        position: str = 'end'
    ) -> np.ndarray:
        """
        添加静音

        Args:
            audio: 音频数据
            duration_seconds: 静音时长（秒）
            sample_rate: 采样率
            position: 位置 ('start', 'end', 'both')

        Returns:
            添加静音后的音频
        """
        silence_samples = int(duration_seconds * sample_rate)
        silence = np.zeros(silence_samples, dtype=np.float32)

        if position == 'start':
            return np.concatenate([silence, audio])
        elif position == 'end':
            return np.concatenate([audio, silence])
        elif position == 'both':
            return np.concatenate([silence, audio, silence])
        else:
            return audio

    def apply_eq(
        self,
        audio: np.ndarray,
        eq_settings: Dict[str, float],
        sample_rate: int
    ) -> np.ndarray:
        """
        应用 EQ 均衡器

        Args:
            audio: 音频数据
            eq_settings: EQ 设置 {'low_shelf': dB, 'mid': dB, 'high_shelf': dB}
            sample_rate: 采样率

        Returns:
            处理后的音频
        """
        # 简化的 EQ 实现（使用滤波器）
        processed = audio.copy()

        # Low shelf (低频增强/衰减)
        if 'low_shelf' in eq_settings:
            gain_db = eq_settings['low_shelf']
            freq = 200  # Hz
            b, a = self._design_shelf_filter(freq, gain_db, sample_rate, 'low')
            processed = signal.filtfilt(b, a, processed)

        # High shelf (高频增强/衰减)
        if 'high_shelf' in eq_settings:
            gain_db = eq_settings['high_shelf']
            freq = 4000  # Hz
            b, a = self._design_shelf_filter(freq, gain_db, sample_rate, 'high')
            processed = signal.filtfilt(b, a, processed)

        return processed.astype(np.float32)

    def _design_shelf_filter(
        self,
        freq: float,
        gain_db: float,
        sample_rate: int,
        shelf_type: str
    ):
        """
        设计 shelf 滤波器

        Args:
            freq: 截止频率
            gain_db: 增益 (dB)
            sample_rate: 采样率
            shelf_type: 'low' 或 'high'

        Returns:
            (b, a) 滤波器系数
        """
        # 简化实现：使用 scipy 的 butter 滤波器
        # 实际应用中应使用更精确的 shelf 滤波器设计
        nyquist = sample_rate / 2
        normalized_freq = freq / nyquist

        if shelf_type == 'low':
            b, a = signal.butter(2, normalized_freq, btype='low')
        else:
            b, a = signal.butter(2, normalized_freq, btype='high')

        # 应用增益
        gain_linear = 10 ** (gain_db / 20)
        b = b * gain_linear

        return b, a

    def add_breath_sound(
        self,
        audio: np.ndarray,
        duration_seconds: float = 0.3,
        sample_rate: int = 16000,
        position: str = 'start'
    ) -> np.ndarray:
        """
        添加呼吸音效果

        Args:
            audio: 音频数据
            duration_seconds: 呼吸音时长
            sample_rate: 采样率
            position: 位置

        Returns:
            添加呼吸音后的音频
        """
        # 生成呼吸音（低通滤波的噪声）
        breath_samples = int(duration_seconds * sample_rate)
        noise = np.random.randn(breath_samples).astype(np.float32)

        # 低通滤波
        b, a = signal.butter(4, 500 / (sample_rate / 2), btype='low')
        breath = signal.filtfilt(b, a, noise)

        # 归一化
        breath = breath / np.max(np.abs(breath)) * 0.3

        # 淡入淡出
        fade_samples = int(0.1 * sample_rate)
        breath[:fade_samples] *= np.linspace(0, 1, fade_samples)
        breath[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        # 添加到音频
        if position == 'start':
            return np.concatenate([breath, audio])
        else:
            return np.concatenate([audio, breath])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_audio_processor.py -v`
Expected: PASS

- [ ] **Step 5: Commit audio processor**

```bash
git add src/tts/audio_processor.py tests/test_audio_processor.py
git commit -m "feat: add audio post-processor with EQ and effects"
```

---

## Task 5: TTS 流式管理器

**Files:**
- Create: `src/tts/tts_streamer.py`
- Test: `tests/test_tts_streamer.py`

- [ ] **Step 1: Write the failing test for TTS streamer**

```python
# tests/test_tts_streamer.py
import pytest
import asyncio
from src.tts.tts_streamer import TTSStreamer
from src.models.tts_config import TTSConfig
from src.vad.interrupt_handler import InterruptHandler


@pytest.mark.asyncio
async def test_tts_streamer_creation():
    """测试 TTS 流式管理器创建"""
    config = TTSConfig()
    streamer = TTSStreamer(config)

    assert streamer.config == config


@pytest.mark.asyncio
async def test_stream_synthesis():
    """测试流式合成"""
    config = TTSConfig()
    streamer = TTSStreamer(config)

    # 流式合成
    audio_chunks = []
    async for chunk in streamer.stream_synthesize("你好世界"):
        audio_chunks.append(chunk)

    assert len(audio_chunks) > 0


@pytest.mark.asyncio
async def test_stream_with_interrupt():
    """测试带打断的流式合成"""
    config = TTSConfig()
    interrupt_handler = InterruptHandler()
    streamer = TTSStreamer(config, interrupt_handler)

    # 触发打断
    interrupt_handler.trigger_interrupt()

    # 尝试合成
    audio_chunks = []
    with pytest.raises(Exception):  # 应该抛出打断异常
        async for chunk in streamer.stream_synthesize("测试打断"):
            audio_chunks.append(chunk)


@pytest.mark.asyncio
async def test_stream_with_director_commands():
    """测试带导演指令的流式合成"""
    config = TTSConfig()
    streamer = TTSStreamer(config)

    # 包含导演指令的文本
    text = "[加速]快速说话[减速]慢速说话"

    audio_chunks = []
    async for chunk in streamer.stream_synthesize(text):
        audio_chunks.append(chunk)

    assert len(audio_chunks) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tts_streamer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.tts.tts_streamer'"

- [ ] **Step 3: Implement TTS streamer**

```python
# src/tts/tts_streamer.py
import asyncio
from typing import AsyncIterator, Optional
import numpy as np
import logging

from src.models.tts_config import TTSConfig
from src.tts.edge_tts_client import EdgeTTSClient
from src.tts.director_parser import DirectorParser
from src.tts.audio_processor import AudioProcessor
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException

logger = logging.getLogger(__name__)


class TTSStreamer:
    """TTS 流式管理器"""

    def __init__(
        self,
        config: TTSConfig,
        interrupt_handler: Optional[InterruptHandler] = None
    ):
        """
        初始化 TTS 流式管理器

        Args:
            config: TTS 配置
            interrupt_handler: 打断处理器
        """
        self.config = config
        self.interrupt_handler = interrupt_handler
        self.director_parser = DirectorParser()
        self.audio_processor = AudioProcessor()
        self.tts_client = EdgeTTSClient(config)

    async def stream_synthesize(
        self,
        text: str,
        apply_director_commands: bool = True
    ) -> AsyncIterator[bytes]:
        """
        流式合成文本

        Args:
            text: 要合成的文本（可能包含导演指令）
            apply_director_commands: 是否应用导演指令

        Yields:
            音频数据块
        """
        # 解析导演指令
        clean_text, commands = self.director_parser.parse(text)

        logger.info(f"Synthesizing: {clean_text[:50]}...")
        logger.debug(f"Director commands: {len(commands)}")

        # 应用指令到配置
        if apply_director_commands and commands:
            config = self.director_parser.apply_commands_to_config(
                commands,
                self.config
            )
            self.tts_client = EdgeTTSClient(config)

        # 流式合成
        try:
            async for chunk in self.tts_client.synthesize(clean_text):
                # 检查打断
                if self.interrupt_handler:
                    await self.interrupt_handler.check_and_raise()

                yield chunk

        except VADInterruptException:
            logger.info("TTS synthesis interrupted by user")
            raise

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise

    async def synthesize_with_effects(
        self,
        text: str,
        add_breath: bool = False,
        eq_settings: Optional[dict] = None
    ) -> AsyncIterator[bytes]:
        """
        合成并添加音效

        Args:
            text: 文本
            add_breath: 是否添加呼吸音
            eq_settings: EQ 设置

        Yields:
            音频数据块
        """
        # 收集所有音频块
        audio_chunks = []
        async for chunk in self.stream_synthesize(text):
            audio_chunks.append(chunk)

        if not audio_chunks:
            return

        # 转换为 numpy 数组
        # 注意：Edge TTS 返回 MP3 格式，需要解码
        # 这里简化处理，实际需要使用 pydub 或 ffmpeg 解码
        # TODO: 实现 MP3 解码

        # 暂时直接返回原始数据
        for chunk in audio_chunks:
            yield chunk
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tts_streamer.py -v`
Expected: PASS

- [ ] **Step 5: Commit TTS streamer**

```bash
git add src/tts/tts_streamer.py tests/test_tts_streamer.py
git commit -m "feat: add TTS streamer with director commands and interrupt support"
```

---

## Task 6: 集成到 WebSocket 服务

**Files:**
- Modify: `src/server.py`
- Test: `tests/test_tts_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_tts_integration.py
import pytest
from fastapi.testclient import TestClient
from src.server import app


client = TestClient(app)


def test_websocket_tts_integration():
    """测试 WebSocket 与 TTS 集成"""
    with client.websocket_connect("/ws/test-tts") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送文本输入
        websocket.send_json({
            "type": "text_input",
            "content": "你好，请讲一个故事",
            "session_id": "test-tts"
        })

        # 接收状态更新
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 接收文本流
        text_chunks = []
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "text_chunk":
                text_chunks.append(msg["content"])
                if msg["is_final"]:
                    break

        # 接收音频流
        audio_chunks = []
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "audio":
                audio_chunks.append(msg["data"])
            elif msg["type"] == "status" and msg["status"] == "listening":
                break

        # 验证
        assert len(text_chunks) > 0
        assert len(audio_chunks) > 0


def test_websocket_tts_with_director_commands():
    """测试带导演指令的 TTS"""
    with client.websocket_connect("/ws/test-director") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送带导演指令的文本
        websocket.send_json({
            "type": "text_input",
            "content": "[加速]快速说话[减速]慢速说话",
            "session_id": "test-director"
        })

        # 接收响应
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 验证生成了音频
        audio_count = 0
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "audio":
                audio_count += 1
            elif msg["type"] == "status" and msg["status"] == "listening":
                break

        assert audio_count > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tts_integration.py -v`
Expected: FAIL (TTS not integrated yet)

- [ ] **Step 3: Integrate TTS into server**

```python
# src/server.py (modify handle_text_input function)
from tts.tts_streamer import TTSStreamer
from models.tts_config import TTSConfig

# 全局 TTS 流式管理器
tts_config = TTSConfig()
tts_streamers = {}


async def handle_text_input(session_id: str, message: TextInputMessage):
    """处理文本输入"""
    print(f"[Session {session_id}] Text input: {message.content}")

    # 更新状态
    state = manager.get_session_state(session_id)
    if state:
        state.update_activity()

    # 发送处理状态
    await manager.send_status(session_id, "processing")

    try:
        # 创建 TTS 流式管理器
        if session_id not in tts_streamers:
            interrupt_handler = interrupt_handlers.get(session_id)
            tts_streamers[session_id] = TTSStreamer(
                tts_config,
                interrupt_handler
            )

        streamer = tts_streamers[session_id]

        # 流式合成音频
        audio_chunks = []
        async for chunk in streamer.stream_synthesize(message.content):
            audio_chunks.append(chunk)

            # 发送音频块
            await manager.send_audio(session_id, chunk)

        # 更新对话历史
        if state:
            state.add_interaction(message.content, "audio_response")

        # 发送完成状态
        await manager.send_status(session_id, "listening")

    except VADInterruptException:
        print(f"[Session {session_id}] TTS interrupted")
        await manager.send_status(session_id, "listening")

    except Exception as e:
        print(f"[Session {session_id}] TTS error: {e}")
        await manager.send_error(
            session_id,
            "TTS_ERROR",
            str(e),
            recoverable=True
        )
        await manager.send_status(session_id, "listening")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tts_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit integration**

```bash
git add src/server.py tests/test_tts_integration.py
git commit -m "feat: integrate TTS into WebSocket server"
```

---

## Task 7: 性能测试

**Files:**
- Create: `tests/test_tts_performance.py`

- [ ] **Step 1: Write performance test**

```python
# tests/test_tts_performance.py
import pytest
import asyncio
import time
from src.tts.tts_streamer import TTSStreamer
from src.models.tts_config import TTSConfig


@pytest.mark.asyncio
async def test_tts_first_chunk_latency():
    """测试首字延迟"""
    config = TTSConfig()
    streamer = TTSStreamer(config)

    # 测试文本
    text = "你好世界"

    # 测量首字延迟
    start = time.perf_counter()
    first_chunk_time = None

    async for chunk in streamer.stream_synthesize(text):
        if first_chunk_time is None:
            first_chunk_time = time.perf_counter() - start
            break

    print(f"\nTTS First Chunk Latency: {first_chunk_time * 1000:.2f} ms")

    # 验证延迟 < 200ms
    assert first_chunk_time < 0.2, f"First chunk latency {first_chunk_time}s exceeds 200ms"


@pytest.mark.asyncio
async def test_tts_throughput():
    """测试 TTS 吞吐量"""
    config = TTSConfig()
    streamer = TTSStreamer(config)

    # 测试长文本
    text = "这是一个测试文本。" * 10

    start = time.perf_counter()
    chunk_count = 0

    async for chunk in streamer.stream_synthesize(text):
        chunk_count += 1

    end = time.perf_counter()
    duration = end - start

    print(f"\nTTS Throughput:")
    print(f"  Total chunks: {chunk_count}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Chunks/second: {chunk_count / duration:.2f}")


@pytest.mark.asyncio
async def test_tts_concurrent_synthesis():
    """测试并发合成"""
    config = TTSConfig()

    # 创建多个合成任务
    tasks = []
    for i in range(5):
        streamer = TTSStreamer(config)
        task = streamer.stream_synthesize(f"测试文本 {i}")
        tasks.append(task)

    # 并发执行
    start = time.perf_counter()

    results = await asyncio.gather(
        *[collect_chunks(task) for task in tasks],
        return_exceptions=True
    )

    end = time.perf_counter()
    duration = end - start

    print(f"\nConcurrent Synthesis:")
    print(f"  Tasks: 5")
    print(f"  Duration: {duration:.2f}s")


async def collect_chunks(async_iterator):
    """收集异步迭代器的所有块"""
    chunks = []
    async for chunk in async_iterator:
        chunks.append(chunk)
    return chunks
```

- [ ] **Step 2: Run performance test**

Run: `pytest tests/test_tts_performance.py -v -s`
Expected: PASS with performance metrics printed

- [ ] **Step 3: Commit performance tests**

```bash
git add tests/test_tts_performance.py
git commit -m "test: add TTS performance tests"
```

---

## 验收标准

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 性能测试通过（首字延迟 < 200ms）
- [ ] 导演指令正确解析和应用
- [ ] 打断机制正常工作
- [ ] 代码覆盖率 > 80%

---

## 下一步

完成阶段3后，继续：

- **阶段4**: LLM 流式生成模块（Claude API）
- **阶段5**: 状态管理 + 导演指令模块
- **阶段6**: 集成测试 + 性能优化

---

**文档版本**: v1.0
**最后更新**: 2026-04-25
**作者**: Claude Sonnet 4.6
