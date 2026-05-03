"""文本分类器测试"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from src.nlp.text_classifier import TextClassifier


def test_classifier_initialization():
    """测试分类器初始化"""
    classifier = TextClassifier()
    assert classifier is not None


def test_classifier_classify_intent():
    """测试意图分类"""
    classifier = TextClassifier()
    text = "我想听一个故事"
    intent = classifier.classify_intent(text)
    assert intent in ['story', 'chat', 'question', 'command', 'unknown']


def test_classifier_classify_topic():
    """测试主题分类"""
    classifier = TextClassifier()
    text = "今天天气怎么样"
    topic = classifier.classify_topic(text)
    assert topic in ['weather', 'news', 'entertainment', 'education', 'other']


def test_classifier_empty_input():
    """测试空输入"""
    classifier = TextClassifier()
    intent = classifier.classify_intent("")
    assert intent == 'unknown'
    topic = classifier.classify_topic("")
    assert topic == 'other'


def test_classifier_none_input():
    """测试None输入"""
    classifier = TextClassifier()
    intent = classifier.classify_intent(None)
    assert intent == 'unknown'
    topic = classifier.classify_topic(None)
    assert topic == 'other'
