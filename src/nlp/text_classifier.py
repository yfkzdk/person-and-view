"""文本分类器 - 基于规则的意图和主题分类"""

from typing import Optional


class TextClassifier:
    """
    文本分类器

    基于关键词和规则进行意图识别和主题分类
    """

    # 意图关键词
    INTENT_KEYWORDS = {
        'story': ['故事', '讲', '听', '童话', '寓言'],
        'question': ['什么', '怎么', '为什么', '如何', '哪', '吗', '？'],
        'command': ['打开', '关闭', '播放', '停止', '开始', '结束'],
        'chat': ['聊天', '说话', '聊聊', '谈谈']
    }

    # 主题关键词
    TOPIC_KEYWORDS = {
        'weather': ['天气', '温度', '下雨', '晴天', '阴天', '风'],
        'news': ['新闻', '消息', '报道', '最新', '发生'],
        'entertainment': ['电影', '音乐', '游戏', '娱乐', '明星'],
        'education': ['学习', '教育', '知识', '课程', '考试']
    }

    def __init__(self):
        """初始化分类器"""
        pass

    def classify_intent(self, text: Optional[str]) -> str:
        """
        意图分类

        Args:
            text: 输入文本

        Returns:
            str: 意图类型
        """
        if not text or not text.strip():
            return 'unknown'

        # 检查关键词
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return intent

        return 'chat'  # 默认为聊天

    def classify_topic(self, text: Optional[str]) -> str:
        """
        主题分类

        Args:
            text: 输入文本

        Returns:
            str: 主题类型
        """
        if not text or not text.strip():
            return 'other'

        # 检查关键词
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return topic

        return 'other'
