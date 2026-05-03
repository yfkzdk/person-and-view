"""
高级人物蒸馏器 - 参考 yourself-skill-master 的双层架构

核心改进：
1. 双层架构：Self Memory + Persona
2. 多数据源支持：聊天记录、日记、社交媒体
3. 5层人格结构：硬规则→身份→说话风格→情感模式→人际行为
4. 进化机制：增量更新、对话纠正
"""
import json
import re
from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime

from src.models.person_profile import (
    PersonProfile,
    PersonalityTrait,
    SpeakingStyle,
    ExampleDialogue
)


class SelfMemory:
    """
    自我记忆层 - Part A

    包含：
    - 个人经历
    - 核心价值观
    - 生活习惯
    - 重要记忆
    - 人际关系
    - 成长轨迹
    """

    def __init__(self):
        self.personal_experiences: List[Dict] = []
        self.core_values: List[str] = []
        self.life_habits: List[str] = []
        self.important_memories: List[Dict] = []
        self.relationships: Dict[str, str] = {}
        self.growth_trajectory: List[str] = []

    def add_experience(self, event: str, time: str, location: str = "", emotion: str = ""):
        """添加个人经历"""
        self.personal_experiences.append({
            "event": event,
            "time": time,
            "location": location,
            "emotion": emotion
        })

    def add_memory(self, content: str, time: str, importance: float = 0.5):
        """添加重要记忆"""
        self.important_memories.append({
            "content": content,
            "time": time,
            "importance": importance
        })

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "personal_experiences": self.personal_experiences,
            "core_values": self.core_values,
            "life_habits": self.life_habits,
            "important_memories": self.important_memories,
            "relationships": self.relationships,
            "growth_trajectory": self.growth_trajectory
        }


class PersonaLayer:
    """
    人格层 - Part B

    5层结构：
    1. 硬规则层 - 绝对不可违反的规则
    2. 身份层 - 基本身份认同
    3. 说话风格层 - 语言习惯
    4. 情感模式层 - 情绪反应
    5. 人际行为层 - 社交模式
    """

    def __init__(self):
        # Layer 1: 硬规则
        self.hard_rules: List[str] = []

        # Layer 2: 身份
        self.identity: Dict = {
            "name": "",
            "role": "",
            "background": "",
            "mbti": "",
            "zodiac": ""
        }

        # Layer 3: 说话风格
        self.speaking_style: Dict = {
            "tone": "",  # 语气
            "catchphrases": [],  # 口头禅
            "vocabulary_level": "",  # 词汇水平
            "sentence_patterns": [],  # 句式习惯
            "filler_words": []  # 口头填充词
        }

        # Layer 4: 情感模式
        self.emotional_patterns: Dict = {
            "triggers": {},  # 情绪触发点
            "responses": {},  # 情绪反应
            "coping_mechanisms": []  # 应对机制
        }

        # Layer 5: 人际行为
        self.interpersonal_behavior: Dict = {
            "communication_style": "",  # 沟通风格
            "conflict_resolution": "",  # 冲突解决
            "intimacy_level": "",  # 亲密程度
            "social_energy": ""  # 社交能量
        }

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "hard_rules": self.hard_rules,
            "identity": self.identity,
            "speaking_style": self.speaking_style,
            "emotional_patterns": self.emotional_patterns,
            "interpersonal_behavior": self.interpersonal_behavior
        }


class AdvancedPersonDistiller:
    """
    高级人物蒸馏器 - 参考 yourself-skill-master

    支持从多种数据源蒸馏人物特征
    """

    def __init__(self):
        # 情绪词汇映射
        self.emotion_keywords = {
            "焦虑": ["担心", "紧张", "不安", "焦虑", "害怕"],
            "沮丧": ["难过", "失望", "沮丧", "失落", "灰心"],
            "愤怒": ["生气", "愤怒", "恼火", "烦躁", "不满"],
            "开心": ["高兴", "开心", "快乐", "兴奋", "满足"],
            "困惑": ["困惑", "迷茫", "不解", "疑惑", "搞不懂"]
        }

        # MBTI特征
        self.mbti_traits = {
            "INTJ": ["独立", "理性", "战略思维", "完美主义"],
            "INFP": ["理想主义", "共情", "创意", "内向"],
            "ENTP": ["创新", "辩论", "灵活", "外向"],
            # ... 其他类型
        }

    def distill_from_chat_history(
        self,
        name: str,
        role: str,
        chat_messages: List[Dict],  # [{"time": "...", "content": "...", "emotion": "..."}]
        basic_info: Dict = None
    ) -> Tuple[SelfMemory, PersonaLayer]:
        """
        从聊天记录蒸馏人物特征

        Args:
            name: 人物名称
            role: 角色
            chat_messages: 聊天记录
            basic_info: 基本信息 {"age": 25, "mbti": "INTJ", "zodiac": "摩羯座"}

        Returns:
            (SelfMemory, PersonaLayer)
        """
        # 初始化
        self_memory = SelfMemory()
        persona = PersonaLayer()

        # Layer 2: 身份
        persona.identity["name"] = name
        persona.identity["role"] = role

        if basic_info:
            persona.identity["age"] = basic_info.get("age", "")
            persona.identity["mbti"] = basic_info.get("mbti", "")
            persona.identity["zodiac"] = basic_info.get("zodiac", "")

        # 分析聊天记录
        speaking_patterns = Counter()
        emotional_triggers = {}
        important_events = []

        for msg in chat_messages:
            content = msg.get("content", "")
            time = msg.get("time", "")
            emotion = msg.get("emotion", "")

            # 提取说话模式
            sentences = re.split(r'[。！？\n]', content)
            for sentence in sentences:
                if len(sentence) > 5:
                    # 提取句式
                    speaking_patterns[sentence[:10]] += 1

            # 提取情绪触发点
            if emotion:
                if emotion not in emotional_triggers:
                    emotional_triggers[emotion] = []
                emotional_triggers[emotion].append(content[:50])

            # 提取重要事件
            if any(keyword in content for keyword in ["我决定", "我选择了", "我终于"]):
                important_events.append({
                    "event": content,
                    "time": time
                })

        # Layer 3: 说话风格
        top_patterns = [p[0] for p in speaking_patterns.most_common(10)]
        persona.speaking_style["sentence_patterns"] = top_patterns

        # 提取口头禅（高频短语）
        catchphrases = self._extract_catchphrases(chat_messages)
        persona.speaking_style["catchphrases"] = catchphrases

        # Layer 4: 情感模式
        persona.emotional_patterns["triggers"] = emotional_triggers

        # Self Memory: 重要事件
        for event in important_events:
            self_memory.add_memory(
                content=event["event"],
                time=event["time"],
                importance=0.8
            )

        return self_memory, persona

    def _extract_catchphrases(self, messages: List[Dict]) -> List[str]:
        """提取口头禅"""
        # 简化实现：提取高频短语
        all_text = " ".join([m.get("content", "") for m in messages])

        # 常见口头禅模式
        patterns = [
            r'我(总是|经常|从来).{1,5}',
            r'(其实|说实话|老实说).{1,10}',
            r'(你知道|你懂|明白吗).{0,5}'
        ]

        catchphrases = []
        for pattern in patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                catchphrases.extend(matches[:3])

        return list(set(catchphrases))[:10]

    def generate_system_prompt(
        self,
        self_memory: SelfMemory,
        persona: PersonaLayer
    ) -> str:
        """
        生成完整的系统提示词

        Returns:
            系统提示词
        """
        prompt_parts = []

        # Part A: Self Memory
        prompt_parts.append("# 自我记忆")
        prompt_parts.append(f"\n## 身份\n{persona.identity['name']}，{persona.identity['role']}")

        if persona.identity.get("mbti"):
            prompt_parts.append(f"\nMBTI: {persona.identity['mbti']}")
        if persona.identity.get("zodiac"):
            prompt_parts.append(f"星座: {persona.identity['zodiac']}")

        # 重要记忆
        if self_memory.important_memories:
            prompt_parts.append("\n## 重要记忆")
            for memory in self_memory.important_memories[:5]:
                prompt_parts.append(f"- {memory['content'][:100]}")

        # Part B: Persona
        prompt_parts.append("\n\n# 人格模型")

        # Layer 1: 硬规则
        if persona.hard_rules:
            prompt_parts.append("\n## 绝对规则")
            for rule in persona.hard_rules:
                prompt_parts.append(f"- {rule}")

        # Layer 3: 说话风格
        if persona.speaking_style["catchphrases"]:
            prompt_parts.append("\n## 说话风格")
            prompt_parts.append(f"口头禅: {', '.join(persona.speaking_style['catchphrases'])}")

        if persona.speaking_style["sentence_patterns"]:
            prompt_parts.append("\n常用句式:")
            for pattern in persona.speaking_style["sentence_patterns"][:5]:
                prompt_parts.append(f"- {pattern}...")

        # Layer 4: 情感模式
        if persona.emotional_patterns["triggers"]:
            prompt_parts.append("\n## 情绪反应")
            for emotion, triggers in list(persona.emotional_patterns["triggers"].items())[:3]:
                prompt_parts.append(f"- 当感到{emotion}时: {triggers[0]}")

        # 行为指导
        prompt_parts.append("\n\n## 行为指导")
        prompt_parts.append("1. 始终保持角色一致性")
        prompt_parts.append("2. 使用你的口头禅和句式")
        prompt_parts.append("3. 根据情绪触发点调整回复")
        prompt_parts.append("4. 引用重要记忆增强真实感")

        return "\n".join(prompt_parts)


# 使用示例
if __name__ == "__main__":
    # 示例聊天记录
    sample_messages = [
        {"time": "2024-01-01", "content": "我决定开始学习Python了", "emotion": "开心"},
        {"time": "2024-01-02", "content": "说实话，这个项目挺难的", "emotion": "困惑"},
        {"time": "2024-01-03", "content": "我终于搞定了！", "emotion": "开心"},
    ]

    # 蒸馏
    distiller = AdvancedPersonDistiller()
    self_memory, persona = distiller.distill_from_chat_history(
        name="小明",
        role="程序员",
        chat_messages=sample_messages,
        basic_info={"age": 25, "mbti": "INTJ", "zodiac": "摩羯座"}
    )

    # 生成系统提示词
    prompt = distiller.generate_system_prompt(self_memory, persona)

    print("=" * 80)
    print("蒸馏结果")
    print("=" * 80)
    print(prompt)
