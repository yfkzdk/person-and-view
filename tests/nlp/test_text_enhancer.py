"""文本增强器测试"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from src.nlp.text_enhancer import TextEnhancer


def test_enhancer_initialization():
    """测试增强器初始化"""
    enhancer = TextEnhancer()
    assert enhancer is not None


def test_enhancer_extract_key_phrases():
    """测试关键短语提取"""
    enhancer = TextEnhancer()
    text = "自然语言处理是人工智能的重要分支"
    phrases = enhancer.extract_key_phrases(text)
    assert isinstance(phrases, list)
    assert len(phrases) > 0


def test_enhancer_summarize():
    """测试文本摘要"""
    enhancer = TextEnhancer()
    text = "自然语言处理是人工智能的重要分支。它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法。自然语言处理是一门融语言学、计算机科学、数学于一体的科学。"
    summary = enhancer.summarize(text, max_length=50)
    assert isinstance(summary, str)
    assert len(summary) <= 50


def test_enhancer_correct_text():
    """测试文本纠错"""
    enhancer = TextEnhancer()
    text = "我想听一个故事"
    corrected = enhancer.correct_text(text)
    assert isinstance(corrected, str)
    assert corrected == text


def test_enhancer_empty_input():
    """测试空输入"""
    enhancer = TextEnhancer()
    phrases = enhancer.extract_key_phrases("")
    assert phrases == []
    summary = enhancer.summarize("")
    assert summary == ""


def test_enhancer_none_input():
    """测试None输入"""
    enhancer = TextEnhancer()
    phrases = enhancer.extract_key_phrases(None)
    assert phrases == []
    summary = enhancer.summarize(None)
    assert summary == ""
    corrected = enhancer.correct_text(None)
    assert corrected == ""