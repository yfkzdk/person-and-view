"""文本增强器 - 关键短语提取、摘要、纠错"""

from typing import List, Optional
import re


class TextEnhancer:
    """
    文本增强器

    提供关键短语提取、文本摘要、文本纠错等功能
    """

    def __init__(self):
        """初始化增强器"""
        pass

    def extract_key_phrases(self, text: Optional[str], top_k: int = 5) -> List[str]:
        """
        提取关键短语

        Args:
            text: 输入文本
            top_k: 返回前K个短语

        Returns:
            List[str]: 关键短语列表
        """
        if not text or not text.strip():
            return []

        # 简单实现：提取2-4字的中文短语
        pattern = r'[一-龥]{2,4}'
        phrases = re.findall(pattern, text)

        # 去重并返回前K个
        unique_phrases = list(dict.fromkeys(phrases))

        return unique_phrases[:top_k]

    def summarize(self, text: Optional[str], max_length: int = 100) -> str:
        """
        文本摘要

        Args:
            text: 输入文本
            max_length: 最大长度

        Returns:
            str: 摘要文本
        """
        if not text or not text.strip():
            return ""

        # 简单实现：截取前max_length个字符
        if len(text) <= max_length:
            return text

        # 尝试在句号处截断
        truncated = text[:max_length]
        last_period = truncated.rfind('。')

        if last_period > max_length * 0.5:
            return truncated[:last_period + 1]
        else:
            return truncated + '...'

    def correct_text(self, text: Optional[str]) -> str:
        """
        文本纠错

        Args:
            text: 输入文本

        Returns:
            str: 纠错后的文本
        """
        if not text or not text.strip():
            return ""

        # 简单实现：去除多余空格
        corrected = re.sub(r'\s+', ' ', text)

        return corrected.strip()