"""
Silero VAD 监控器
"""
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
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model_name = model_name

        if sample_rate not in [8000, 16000]:
            raise ValueError("Sample rate must be 8000 or 16000")

        self.model = None
        self.utils = None
        self._torch = None
        self._load_model()
        logger.info(f"VAD model loaded: {model_name}")

    def _load_model(self):
        """加载 Silero VAD 模型"""
        try:
            import torch
            self._torch = torch

            import os
            os.environ['TORCH_HOME'] = os.path.join(os.path.expanduser('~'), '.cache', 'torch')

            cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'torch', 'hub', 'snakers4_silero-vad_master')

            if os.path.exists(cache_dir):
                model, utils = torch.hub.load(
                    repo_or_dir=cache_dir,
                    model=self.model_name,
                    source='local',
                    force_reload=False,
                    onnx=False
                )
            else:
                model, utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model=self.model_name,
                    force_reload=False,
                    onnx=False,
                    trust_repo=True,
                    skip_validation=True
                )

            model.eval()
            self.model = model
            self.utils = utils
        except Exception as e:
            logger.warning(f"Failed to load VAD model (torch not available?): {e}")
            self.model = None
            self.utils = None

    def detect_speech(self, audio: np.ndarray) -> bool:
        if self.model is None:
            return False
        prob = self.get_speech_probability(audio)
        return prob > self.threshold

    def get_speech_probability(self, audio: np.ndarray) -> float:
        if self.model is None or self._torch is None:
            return 0.0

        audio_tensor = self._torch.from_numpy(audio)
        with self._torch.no_grad():
            speech_prob = self.model(audio_tensor, self.sample_rate).item()

        return speech_prob

    def reset(self):
        if self.model is not None:
            self.model.reset_states()

    def __del__(self):
        if hasattr(self, 'model') and self.model is not None:
            del self.model
