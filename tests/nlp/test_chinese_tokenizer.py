"""中文分词器测试"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pytest
from src.nlp.chinese_tokenizer import ChineseTokenizer


def test_tokenizer_initialization():
    """测试分词器初始化"""
    tokenizer = ChineseTokenizer()
    assert tokenizer is not None


def test_tokenizer_cut():
    """测试分词功能"""
    tokenizer = ChineseTokenizer()
    text = "我爱自然语言处理"
    tokens = tokenizer.cut(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert "我" in tokens or "我爱" in tokens


def test_tokenizer_pos_tagging():
    """测试词性标注"""
    tokenizer = ChineseTokenizer()
    text = "我爱自然语言处理"
    tagged = tokenizer.pos_tag(text)
    assert isinstance(tagged, list)
    assert len(tagged) > 0
    for item in tagged:
        assert len(item) == 2
        assert isinstance(item[0], str)
        assert isinstance(item[1], str)


def test_tokenizer_extract_keywords():
    """测试关键词提取"""
    tokenizer = ChineseTokenizer()
    text = "自然语言处理是人工智能的重要分支，它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法"
    keywords = tokenizer.extract_keywords(text, top_k=3)
    assert isinstance(keywords, list)
    assert len(keywords) <= 3
    assert "自然语言处理" in keywords or "人工智能" in keywords


def test_tokenizer_custom_dict():
    """测试自定义词典"""
    tokenizer = ChineseTokenizer()
    tokenizer.add_word("自然语言处理")
    text = "自然语言处理很有趣"
    tokens = tokenizer.cut(text)
    assert "自然语言处理" in tokens


def test_tokenizer_empty_input():
    """测试空输入"""
    tokenizer = ChineseTokenizer()
    tokens = tokenizer.cut("")
    assert tokens == []
    tokens = tokenizer.cut(None)
    assert tokens == []