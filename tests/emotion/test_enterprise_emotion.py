"""测试企业级多模态情绪检测系统"""
import pytest
import numpy as np
from src.emotion import (
    MultimodalEmotionDetector,
    TextEmotionAnalyzer,
    EmotionFusionEngine,
    EmotionState
)
from src.emotion.enterprise_emotion import EnterpriseEmotionState as RawEmotionState


class TestTextEmotionAnalyzer:
    """测试文本情绪分析器（关键词 fallback 模式）"""

    @pytest.fixture
    def analyzer(self):
        return TextEmotionAnalyzer()

    def test_initialization(self, analyzer):
        """初始化应为 fallback 模式（无 BERT 模型）"""
        assert analyzer.use_fallback is True
        assert analyzer.bert is None

    def test_analyze_positive_text(self, analyzer):
        """开心文本检测"""
        result = analyzer.analyze("今天天气真好，我很开心！")
        assert result.type == "joy"
        assert result.label == "快乐"

    def test_analyze_negative_text(self, analyzer):
        """悲伤文本检测"""
        result = analyzer.analyze("我感到非常难过和失望")
        assert result.type == "sadness"
        assert result.label == "悲伤"

    def test_analyze_angry_text(self, analyzer):
        """愤怒文本检测"""
        result = analyzer.analyze("这让我非常生气和愤怒")
        assert result.type == "anger"
        assert result.label == "愤怒"

    def test_analyze_neutral_text(self, analyzer):
        """中性文本检测"""
        result = analyzer.analyze("今天星期三")
        assert result.type == "neutral"
        assert result.label == "平静"

    def test_analyze_fear_text(self, analyzer):
        """恐惧/焦虑文本检测"""
        result = analyzer.analyze("我真的很担心明天的考试")
        assert result.type == "fear"
        assert result.label == "恐惧"

    def test_multiple_keywords_returns_first_match(self, analyzer):
        """多关键词时返回第一个匹配"""
        result = analyzer.analyze("开心但是又有点害怕")
        assert result.type == "joy"  # joy keywords checked first


class TestEmotionFusionEngine:
    """测试情绪融合引擎"""

    @pytest.fixture
    def engine(self):
        return EmotionFusionEngine()

    def test_fuse_text_only(self, engine):
        """仅文本情绪"""
        text_emotion = RawEmotionState(type="joy", intensity=0.9, confidence=0.8, label="快乐")
        result = engine.fuse(text_emotion, None)
        assert result.type == "joy"

    def test_fuse_audio_only(self, engine):
        """仅音频情绪"""
        audio_emotion = RawEmotionState(type="sadness", intensity=0.85, confidence=0.75, label="悲伤")
        result = engine.fuse(None, audio_emotion)
        assert result.type == "sadness"

    def test_fuse_same_emotion(self, engine):
        """相同情绪融合——强度加权"""
        text_emotion = RawEmotionState(type="joy", intensity=0.9, confidence=0.8, label="快乐")
        audio_emotion = RawEmotionState(type="joy", intensity=0.7, confidence=0.6, label="快乐")
        result = engine.fuse(text_emotion, audio_emotion)
        assert result.type == "joy"
        # 0.9*0.6 + 0.7*0.4 = 0.54 + 0.28 = 0.82
        assert 0.7 < result.intensity < 0.95

    def test_fuse_different_emotions(self, engine):
        """不同情绪时取高置信度"""
        text_emotion = RawEmotionState(type="joy", intensity=0.9, confidence=0.9, label="快乐")
        audio_emotion = RawEmotionState(type="sadness", intensity=0.5, confidence=0.4, label="悲伤")
        result = engine.fuse(text_emotion, audio_emotion)
        assert result.type == "joy"  # text has higher confidence

    def test_fuse_both_none(self, engine):
        """两者都为空时返回中性"""
        result = engine.fuse(None, None)
        assert result.type == "neutral"
        assert result.intensity == 0.5


class TestMultimodalEmotionDetector:
    """测试多模态情绪检测器"""

    @pytest.fixture
    def detector(self):
        return MultimodalEmotionDetector()

    def test_detect_text_only(self, detector):
        """仅文本检测"""
        result = detector.detect(text="我今天特别开心！")
        assert result.type == "joy"

    def test_detect_neutral(self, detector):
        """中性文本检测"""
        result = detector.detect(text="今天的日期是星期三")
        assert result.type == "neutral"

    def test_emotion_trend(self, detector):
        """情绪趋势统计"""
        detector.detect(text="开心")
        detector.detect(text="开心")
        detector.detect(text="难过")
        trend = detector.get_emotion_trend(window=3)
        assert "joy" in trend
        assert "sadness" in trend
        assert abs(trend["joy"] - 2/3) < 0.01

    def test_reset_history(self, detector):
        """重置历史"""
        detector.detect(text="开心")
        detector.reset()
        trend = detector.get_emotion_trend()
        assert len(trend) == 0
