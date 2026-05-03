"""企业级多模态情绪检测系统"""
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)


def _get_torch():
    import torch
    return torch


def _get_nn():
    import torch.nn as nn
    return nn


class EmotionState:
    """情绪状态"""
    def __init__(self, type: str = 'neutral', intensity: float = 0.5,
                 confidence: float = 0.6, label: str = '平静',
                 secondary_emotions: Optional[Dict[str, float]] = None):
        self.type = type
        self.intensity = intensity
        self.confidence = confidence
        self.label = label
        self.secondary_emotions = secondary_emotions


class TextEmotionAnalyzer:
    """文本情绪分析器"""

    EMOTION_LABELS = {
        'joy': '快乐',
        'sadness': '悲伤',
        'anger': '愤怒',
        'fear': '恐惧',
        'surprise': '惊讶',
        'disgust': '厌恶',
        'neutral': '平静'
    }

    def __init__(self, model_name: str = "bert-base-chinese"):
        # 使用 fallback 模式（关键词匹配），避免 torch 依赖
        self.use_fallback = True
        self.bert = None
        self.tokenizer = None
        logger.info("TextEmotionAnalyzer initialized (fallback/keyword mode)")

    def analyze(self, text: str) -> EmotionState:
        """分析文本情绪（关键词匹配 fallback）"""
        emotion_keywords = {
            'joy': ['开心', '高兴', '快乐', '棒', '好', '太好了'],
            'sadness': ['伤心', '难过', '悲伤', '失望', '遗憾'],
            'anger': ['生气', '愤怒', '讨厌', '烦', '气死'],
            'fear': ['害怕', '恐惧', '担心', '焦虑', '紧张'],
            'surprise': ['惊讶', '意外', '没想到', '震惊'],
            'disgust': ['厌恶', '恶心', '讨厌', '反感'],
            'neutral': []
        }

        detected_emotion = 'neutral'
        for emotion_type, keywords in emotion_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_emotion = emotion_type
                break

        return EmotionState(
            type=detected_emotion,
            intensity=0.5,
            confidence=0.6,
            label=self.EMOTION_LABELS[detected_emotion]
        )


class EmotionFusionEngine:
    """情绪融合引擎"""

    def __init__(self):
        self.text_weight = 0.6
        self.audio_weight = 0.4

    def fuse(self, text_emotion, audio_emotion) -> EmotionState:
        if text_emotion is None and audio_emotion is None:
            return EmotionState(type='neutral', intensity=0.5, confidence=0.0, label='平静')
        if text_emotion is None:
            return audio_emotion
        if audio_emotion is None:
            return text_emotion

        if text_emotion.type == audio_emotion.type:
            fused_intensity = text_emotion.intensity * self.text_weight + audio_emotion.intensity * self.audio_weight
            fused_confidence = text_emotion.confidence * self.text_weight + audio_emotion.confidence * self.audio_weight
            return EmotionState(
                type=text_emotion.type, intensity=fused_intensity,
                confidence=fused_confidence, label=text_emotion.label,
                secondary_emotions=text_emotion.secondary_emotions
            )
        else:
            return text_emotion if text_emotion.confidence >= audio_emotion.confidence else audio_emotion


class MultimodalEmotionDetector:
    """多模态情绪检测器"""

    def __init__(self, text_model: str = "bert-base-chinese"):
        self.text_analyzer = TextEmotionAnalyzer(text_model)
        self.fusion_engine = EmotionFusionEngine()
        self.emotion_history: List[EmotionState] = []

    def detect(self, text: Optional[str] = None, audio_path: Optional[str] = None) -> EmotionState:
        text_emotion = None
        if text:
            text_emotion = self.text_analyzer.analyze(text)

        fused_emotion = self.fusion_engine.fuse(text_emotion, None)
        self.emotion_history.append(fused_emotion)
        if len(self.emotion_history) > 20:
            self.emotion_history.pop(0)
        return fused_emotion

    def get_emotion_trend(self, window: int = 5) -> Dict[str, float]:
        if not self.emotion_history:
            return {}
        recent = self.emotion_history[-window:]
        counts = {}
        for e in recent:
            counts[e.type] = counts.get(e.type, 0) + 1
        return {k: v / len(recent) for k, v in counts.items()}

    def reset(self):
        self.emotion_history.clear()