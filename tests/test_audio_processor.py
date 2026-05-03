"""
音频后处理器测试
"""
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


def test_add_breath_sound():
    """测试添加呼吸音"""
    processor = AudioProcessor()

    # 创建测试音频
    audio = np.ones(16000, dtype=np.float32)

    # 添加呼吸音
    with_breath = processor.add_breath_sound(audio, duration_seconds=0.3, sample_rate=16000, position='start')

    # 验证长度增加
    expected_length = 16000 + int(0.3 * 16000)
    assert len(with_breath) == expected_length


def test_concatenate_empty():
    """测试拼接空列表"""
    processor = AudioProcessor()

    result = processor.concatenate([])

    assert len(result) == 0
