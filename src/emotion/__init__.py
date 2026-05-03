"""多模态情绪检测系统"""

from .emotion_aware_dialogue import EmotionAwareResponder, EmotionState, EmotionAnalyzer, EmotionAwareResponder as EmotionResponder
from .emotion_dimensions import EmotionDimension
from .enterprise_emotion import (
    MultimodalEmotionDetector,
    TextEmotionAnalyzer,
    EmotionFusionEngine,
)

__all__ = [
    "EmotionAwareResponder",
    "EmotionState",
    "EmotionDimension",
    "MultimodalEmotionDetector",
    "TextEmotionAnalyzer",
    "EmotionFusionEngine",
    "EmotionAnalyzer",
]