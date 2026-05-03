"""
音频预处理工具测试
"""
import pytest
import numpy as np
from src.utils.audio_utils import resample_audio, normalize_audio, convert_to_int16, convert_to_float32


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


def test_convert_to_int16():
    """测试转换为 int16"""
    audio = np.array([0.5, -0.5, 1.0, -1.0], dtype=np.float32)
    converted = convert_to_int16(audio)

    assert converted.dtype == np.int16
    assert converted[0] == 16383  # 0.5 * 32767
    assert converted[1] == -16383
    assert converted[2] == 32767
    assert converted[3] == -32767


def test_convert_to_float32():
    """测试转换为 float32"""
    audio = np.array([16383, -16383, 32767, -32767], dtype=np.int16)
    converted = convert_to_float32(audio)

    assert converted.dtype == np.float32
    assert abs(converted[0] - 0.5) < 0.01
    assert abs(converted[1] + 0.5) < 0.01
    assert abs(converted[2] - 1.0) < 0.01
    assert abs(converted[3] + 1.0) < 0.01
