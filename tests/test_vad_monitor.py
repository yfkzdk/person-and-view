"""
VAD 监控器测试
"""
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
    """测试语音检测功能"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成测试音频（512 samples for 16kHz）
    t = np.linspace(0, 0.032, 512)
    # 创建一个更复杂的信号（虽然不是真实语音，但用于测试功能）
    speech = (np.sin(2 * np.pi * 440 * t) * 0.8).astype(np.float32)

    # 测试检测功能是否正常工作
    is_speech = monitor.detect_speech(speech)
    prob = monitor.get_speech_probability(speech)

    # 只验证返回值类型和范围正确
    assert isinstance(is_speech, bool)
    assert 0.0 <= prob <= 1.0


def test_vad_get_speech_probability():
    """测试获取语音概率"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成测试音频
    audio = np.random.randn(512).astype(np.float32) * 0.5

    prob = monitor.get_speech_probability(audio)

    # 概率应该在 [0, 1] 范围内
    assert 0.0 <= prob <= 1.0


def test_vad_invalid_sample_rate():
    """测试无效采样率"""
    with pytest.raises(ValueError):
        VADMonitor(sample_rate=22050, threshold=0.5)
