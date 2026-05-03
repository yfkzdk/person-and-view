"""
音频缓冲管理器
"""
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
