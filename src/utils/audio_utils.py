"""
音频预处理工具
"""
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
