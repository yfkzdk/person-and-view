"""PAD情绪维度模型 - Pleasure (愉悦度), Arousal (唤醒度), Dominance (支配度)"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class EmotionDimension:
    """
    PAD三维情绪维度模型

    Pleasure (愉悦度): -1 (不愉悦) 到 1 (愉悦)
    Arousal (唤醒度): -1 (平静) 到 1 (兴奋)
    Dominance (支配度): -1 (被支配) 到 1 (支配)
    """
    pleasure: float
    arousal: float
    dominance: float

    def __post_init__(self):
        """验证维度值在有效范围内"""
        for attr_name in ['pleasure', 'arousal', 'dominance']:
            value = getattr(self, attr_name)
            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"{attr_name} must be between -1.0 and 1.0, got {value}"
                )

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'pleasure': self.pleasure,
            'arousal': self.arousal,
            'dominance': self.dominance
        }
