"""
音频后处理器
"""
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
        normalized_freq = min(freq / nyquist, 0.99)  # 避免超过 Nyquist 频率

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
        fade_samples = int(min(0.1 * sample_rate, len(breath) / 2))
        breath[:fade_samples] *= np.linspace(0, 1, fade_samples)
        breath[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        # 添加到音频
        if position == 'start':
            return np.concatenate([breath, audio])
        else:
            return np.concatenate([audio, breath])
