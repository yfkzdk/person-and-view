"""
音频缓冲测试
"""
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


def test_circular_buffer_clear():
    """测试清空缓冲区"""
    buffer = CircularAudioBuffer(capacity=1024, sample_rate=16000)

    data = np.random.randn(512).astype(np.float32)
    buffer.write(data)

    buffer.clear()

    assert buffer.total_written == 0
    assert buffer.write_pos == 0
    assert np.all(buffer.buffer == 0)


def test_circular_buffer_get_duration():
    """测试获取时长"""
    buffer = CircularAudioBuffer(capacity=16000, sample_rate=16000)

    # 写入 0.5 秒音频
    data = np.random.randn(8000).astype(np.float32)
    buffer.write(data)

    duration = buffer.get_duration()
    assert abs(duration - 0.5) < 0.01
