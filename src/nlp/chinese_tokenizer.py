"""中文分词器 - 使用jieba进行中文分词"""

from typing import List, Tuple, Optional
import jieba
import jieba.posseg as pseg
from jieba.analyse import extract_tags


class ChineseTokenizer:
    """
    中文分词器

    使用jieba进行中文分词、词性标注和关键词提取
    """

    def __init__(self):
        """初始化分词器"""
        pass

    def cut(self, text: Optional[str]) -> List[str]:
        """
        分词

        Args:
            text: 输入文本

        Returns:
            List[str]: 分词结果
        """
        if not text or not text.strip():
            return []

        tokens = list(jieba.cut(text, cut_all=False))
        return tokens

    def cut_all(self, text: Optional[str]) -> List[str]:
        """
        全模式分词

        Args:
            text: 输入文本

        Returns:
            List[str]: 所有可能的分词结果
        """
        if not text or not text.strip():
            return []

        tokens = list(jieba.cut(text, cut_all=True))
        return tokens

    def cut_for_search(self, text: Optional[str]) -> List[str]:
        """
        搜索引擎模式分词

        Args:
            text: 输入文本

        Returns:
            List[str]: 分词结果（适合搜索引擎索引）
        """
        if not text or not text.strip():
            return []

        tokens = list(jieba.cut_for_search(text))
        return tokens

    def pos_tag(self, text: Optional[str]) -> List[Tuple[str, str]]:
        """
        词性标注

        Args:
            text: 输入文本

        Returns:
            List[Tuple[str, str]]: (词, 词性)列表
        """
        if not text or not text.strip():
            return []

        words = pseg.cut(text)
        tagged = [(word, flag) for word, flag in words]

        return tagged

    def extract_keywords(self, text: Optional[str], top_k: int = 10) -> List[str]:
        """
        提取关键词

        Args:
            text: 输入文本
            top_k: 返回前K个关键词

        Returns:
            List[str]: 关键词列表
        """
        if not text or not text.strip():
            return []

        keywords = extract_tags(text, topK=top_k)

        return keywords

    def add_word(self, word: str, freq: Optional[int] = None, tag: Optional[str] = None):
        """
        添加自定义词

        Args:
            word: 词语
            freq: 词频（可选）
            tag: 词性（可选）
        """
        if freq and tag:
            jieba.add_word(word, freq=freq, tag=tag)
        elif freq:
            jieba.add_word(word, freq=freq)
        else:
            jieba.add_word(word)

    def del_word(self, word: str):
        """
        删除词

        Args:
            word: 词语
        """
        jieba.del_word(word)

    def load_userdict(self, file_path: str):
        """
        加载用户自定义词典

        Args:
            file_path: 词典文件路径
        """
        jieba.load_userdict(file_path)