"""
人物技能蒸馏器 - 从对话样本中提取人物特征
"""
import json
import re
from typing import List, Dict, Tuple
from collections import Counter

from src.models.person_profile import (
    PersonProfile,
    PersonalityTrait,
    SpeakingStyle,
    ExampleDialogue
)


class PersonDistiller:
    """人物技能蒸馏器"""

    def __init__(self):
        # 情绪词汇映射
        self.emotion_keywords = {
            "焦虑": ["担心", "紧张", "不安", "焦虑", "害怕"],
            "沮丧": ["难过", "失望", "沮丧", "失落", "灰心"],
            "愤怒": ["生气", "愤怒", "恼火", "烦躁", "不满"],
            "开心": ["高兴", "开心", "快乐", "兴奋", "满足"],
            "困惑": ["困惑", "迷茫", "不解", "疑惑", "搞不懂"]
        }

        # 性格特质关键词
        self.trait_keywords = {
            PersonalityTrait.WARM: ["温暖", "关心", "体贴", "温柔", "善解人意"],
            PersonalityTrait.PROFESSIONAL: ["专业", "严谨", "规范", "系统", "方法"],
            PersonalityTrait.HUMOROUS: ["幽默", "有趣", "搞笑", "调侃", "玩笑"],
            PersonalityTrait.EMPATHETIC: ["理解", "共情", "感受", "体会", "站在...角度"],
            PersonalityTrait.ANALYTICAL: ["分析", "逻辑", "理性", "思考", "推理"],
            PersonalityTrait.CREATIVE: ["创意", "新颖", "独特", "想象", "灵感"],
            PersonalityTrait.PRACTICAL: ["实用", "实际", "具体", "可行", "落地"]
        }

    def distill_from_dialogues(
        self,
        name: str,
        role: str,
        dialogues: List[Tuple[str, str]],
        background: str = ""
    ) -> PersonProfile:
        """
        从对话样本中蒸馏人物特征

        Args:
            name: 人物名称
            role: 人物角色
            dialogues: 对话样本 [(用户输入, 人物回复), ...]
            background: 背景故事

        Returns:
            人物档案
        """
        # 分析性格特质
        personality_traits = self._analyze_personality(dialogues)

        # 分析说话风格
        speaking_style = self._analyze_speaking_style(dialogues)

        # 提取口头禅
        catchphrases = self._extract_catchphrases(dialogues)

        # 分析情绪反应模式
        emotional_responses = self._analyze_emotional_responses(dialogues)

        # 创建示例对话
        example_dialogues = [
            ExampleDialogue(
                user_input=user_input,
                response=response
            )
            for user_input, response in dialogues[:10]  # 最多10个示例
        ]

        # 创建人物档案
        profile = PersonProfile(
            name=name,
            role=role,
            background=background or f"这是{name}，一位{role}。",
            personality_traits=personality_traits,
            speaking_style=speaking_style,
            catchphrases=catchphrases,
            emotional_responses=emotional_responses,
            example_dialogues=example_dialogues
        )

        return profile

    def _analyze_personality(self, dialogues: List[Tuple[str, str]]) -> List[PersonalityTrait]:
        """分析性格特质"""
        trait_scores = Counter()

        for user_input, response in dialogues:
            # 检查回复中的特质关键词
            for trait, keywords in self.trait_keywords.items():
                for keyword in keywords:
                    if keyword in response:
                        trait_scores[trait] += 1

        # 选择得分最高的特质（最多3个）
        top_traits = [trait for trait, _ in trait_scores.most_common(3)]

        return top_traits if top_traits else [PersonalityTrait.WARM]

    def _analyze_speaking_style(self, dialogues: List[Tuple[str, str]]) -> SpeakingStyle:
        """分析说话风格"""
        # 统计回复长度
        response_lengths = [len(response) for _, response in dialogues]
        avg_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0

        # 检查是否有幽默元素
        humor_markers = ["哈哈", "😄", "😂", "有趣", "搞笑"]
        has_humor = any(
            marker in response
            for _, response in dialogues
            for marker in humor_markers
        )

        # 检查是否正式
        formal_markers = ["您好", "请", "感谢", "非常", "专业"]
        is_formal = any(
            marker in response
            for _, response in dialogues
            for marker in formal_markers
        )

        # 判断风格
        if has_humor:
            return SpeakingStyle.PLAYFUL
        elif is_formal:
            return SpeakingStyle.FORMAL
        elif avg_length < 20:
            return SpeakingStyle.CONCISE
        elif avg_length > 100:
            return SpeakingStyle.DETAILED
        else:
            return SpeakingStyle.CASUAL

    def _extract_catchphrases(self, dialogues: List[Tuple[str, str]]) -> List[str]:
        """提取口头禅"""
        # 收集所有回复中的短语
        phrases = []
        for _, response in dialogues:
            # 提取常见的表达模式
            # 例如："我理解你的感受"、"让我想想"等
            common_patterns = [
                r"我理解.*?感受",
                r"让我.*?看",
                r"没问题",
                r"好的",
                r"可以的",
                r"别担心",
                r"放心吧"
            ]

            for pattern in common_patterns:
                matches = re.findall(pattern, response)
                phrases.extend(matches)

        # 统计频率，选择最常见的
        phrase_counter = Counter(phrases)
        catchphrases = [phrase for phrase, _ in phrase_counter.most_common(5)]

        return catchphrases

    def _analyze_emotional_responses(self, dialogues: List[Tuple[str, str]]) -> Dict[str, str]:
        """分析情绪反应模式"""
        emotional_responses = {}

        for user_input, response in dialogues:
            # 检测用户输入中的情绪
            for emotion, keywords in self.emotion_keywords.items():
                if any(keyword in user_input for keyword in keywords):
                    if emotion not in emotional_responses:
                        # 提取回复的前50个字符作为反应模式
                        emotional_responses[emotion] = response[:50] + "..."

        return emotional_responses

    def save_profile(self, profile: PersonProfile, filepath: str):
        """保存人物档案到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile.dict(), f, ensure_ascii=False, indent=2)

    def load_profile(self, filepath: str) -> PersonProfile:
        """从文件加载人物档案"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return PersonProfile(**data)


# 使用示例
if __name__ == "__main__":
    # 示例对话数据
    sample_dialogues = [
        ("我最近感觉很焦虑", "我理解你的感受。焦虑是很正常的情绪反应。能跟我说说，是什么让你感到焦虑吗？"),
        ("我觉得自己很失败", "听起来你现在对自己很失望。但我想告诉你，能够觉察到自己的感受，这本身就是一种勇气。"),
        ("我不知道该怎么办", "别担心，让我们一起来看看。你觉得现在最困扰你的是什么？"),
        ("谢谢你", "不客气！能帮到你我很高兴。记住，任何时候都可以来找我聊聊。"),
    ]

    # 蒸馏人物特征
    distiller = PersonDistiller()
    profile = distiller.distill_from_dialogues(
        name="小云",
        role="心理咨询师",
        dialogues=sample_dialogues,
        background="一位温暖、专业的心理咨询师，擅长倾听和共情。"
    )

    # 输出系统提示词
    print("=" * 80)
    print("蒸馏后的人物档案")
    print("=" * 80)
    print(profile.to_system_prompt())

    # 保存档案
    distiller.save_profile(profile, "person_profile.json")
    print("\n✅ 人物档案已保存到 person_profile.json")
