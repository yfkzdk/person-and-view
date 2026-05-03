"""中文情感分析器 - 使用情感词典和规则进行情感分析"""

from typing import Any, Dict, Optional


class SentimentAnalyzer:
    """
    中文情感分析器

    使用情感词典和规则进行情感极性分析
    """

    # 情感词典（简化版）
    POSITIVE_WORDS = {
        '开心', '高兴', '快乐', '愉快', '幸福', '美好', '喜欢', '爱',
        '棒', '好', '优秀', '出色', '精彩', '完美', '满意', '感谢',
        '希望', '期待', '成功', '胜利', '阳光', '温暖', '甜蜜'
    }

    NEGATIVE_WORDS = {
        '难过', '伤心', '悲伤', '痛苦', '失望', '沮丧', '郁闷', '烦恼',
        '糟糕', '差', '坏', '失败', '错误', '问题', '困难', '麻烦',
        '讨厌', '恨', '愤怒', '生气', '焦虑', '担心', '害怕', '恐惧'
    }

    # 程度副词
    INTENSIFIERS = {
        '非常': 1.5,
        '很': 1.3,
        '特别': 1.5,
        '极其': 1.8,
        '太': 1.6,
        '相当': 1.4,
        '比较': 1.2,
        '有点': 0.8,
        '稍微': 0.7,
        '略微': 0.6
    }

    # 否定词
    NEGATORS = {'不', '没', '无', '非', '未', '别', '莫'}

    def __init__(self):
        """初始化分析器"""
        pass

    def analyze(self, text: Optional[str]) -> Dict[str, Any]:
        """
        分析文本情感

        Args:
            text: 输入文本

        Returns:
            Dict: 情感分析结果
        """
        if not text or not text.strip():
            return {
                'polarity': 'neutral',
                'confidence': 0.0,
                'score': 0.0
            }

        # 计算情感得分
        score = self._calculate_score(text)

        # 确定极性
        if score > 0.1:
            polarity = 'positive'
        elif score < -0.1:
            polarity = 'negative'
        else:
            polarity = 'neutral'

        # 计算置信度
        confidence = min(abs(score), 1.0)

        return {
            'polarity': polarity,
            'confidence': confidence,
            'score': score
        }

    def _calculate_score(self, text: str) -> float:
        """
        计算情感得分

        Args:
            text: 输入文本

        Returns:
            float: 情感得分（-1到1）
        """
        score = 0.0

        # 简单的情感词匹配
        for word in self.POSITIVE_WORDS:
            if word in text:
                score += 0.3

        for word in self.NEGATIVE_WORDS:
            if word in text:
                score -= 0.3

        # 检查程度副词
        for intensifier, multiplier in self.INTENSIFIERS.items():
            if intensifier in text:
                score *= multiplier
                break

        # 检查否定词
        for negator in self.NEGATORS:
            if negator in text:
                score *= -0.5
                break

        # 归一化到-1到1范围
        score = max(-1.0, min(1.0, score))

        return score

    def get_sentiment_words(self, text: str) -> Dict[str, list]:
        """
        提取文本中的情感词

        Args:
            text: 输入文本

        Returns:
            Dict: 正面词和负面词列表
        """
        positive_found = [word for word in self.POSITIVE_WORDS if word in text]
        negative_found = [word for word in self.NEGATIVE_WORDS if word in text]

        return {
            'positive': positive_found,
            'negative': negative_found
        }
