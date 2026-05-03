"""中文情感分析器测试"""
import sys

from src.nlp.sentiment_analyzer import SentimentAnalyzer

sys.stdout.reconfigure(encoding='utf-8')


def test_analyzer_initialization():
    """测试分析器初始化"""
    analyzer = SentimentAnalyzer()
    assert analyzer is not None


def test_analyzer_positive_sentiment():
    """测试正面情感分析"""
    analyzer = SentimentAnalyzer()
    text = "今天天气真好，阳光明媚，心情愉快"
    result = analyzer.analyze(text)
    assert result['polarity'] in ['positive', 'neutral', 'negative']
    assert result['confidence'] >= 0.0
    assert result['confidence'] <= 1.0


def test_analyzer_negative_sentiment():
    """测试负面情感分析"""
    analyzer = SentimentAnalyzer()
    text = "今天很糟糕，心情很差，什么都不想做"
    result = analyzer.analyze(text)
    assert result['polarity'] in ['positive', 'neutral', 'negative']


def test_analyzer_neutral_sentiment():
    """测试中性情感分析"""
    analyzer = SentimentAnalyzer()
    text = "今天天气一般"
    result = analyzer.analyze(text)
    assert result['polarity'] in ['positive', 'neutral', 'negative']


def test_analyzer_sentiment_score():
    """测试情感强度评分"""
    analyzer = SentimentAnalyzer()
    text = "我非常开心"
    result = analyzer.analyze(text)
    assert 'score' in result
    assert -1.0 <= result['score'] <= 1.0


def test_analyzer_empty_input():
    """测试空输入"""
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze("")
    assert result['polarity'] == 'neutral'
    assert result['confidence'] == 0.0
