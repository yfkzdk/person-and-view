"""
人物档案模型 - 定义AI模拟的人物特征
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class PersonalityTrait(str, Enum):
    """性格特质"""
    WARM = "warm"  # 温暖
    PROFESSIONAL = "professional"  # 专业
    HUMOROUS = "humorous"  # 幽默
    SERIOUS = "serious"  # 严肃
    EMPATHETIC = "empathetic"  # 同理心强
    ANALYTICAL = "analytical"  # 理性分析
    CREATIVE = "creative"  # 创意
    PRACTICAL = "practical"  # 务实


class SpeakingStyle(str, Enum):
    """说话风格"""
    CASUAL = "casual"  # 随意
    FORMAL = "formal"  # 正式
    PLAYFUL = "playful"  # 俏皮
    CONCISE = "concise"  # 简洁
    DETAILED = "detailed"  # 详细
    STORYTELLING = "storytelling"  # 叙事性


class ExampleDialogue(BaseModel):
    """示例对话"""
    user_input: str = Field(..., description="用户输入")
    response: str = Field(..., description="人物回复")
    emotion: Optional[str] = Field(None, description="情绪标签")
    context: Optional[str] = Field(None, description="上下文")


class PersonProfile(BaseModel):
    """人物档案"""

    # 基本信息
    name: str = Field(..., description="人物名称")
    role: str = Field(..., description="人物角色/职业")
    background: str = Field(..., description="背景故事")

    # 性格特征
    personality_traits: List[PersonalityTrait] = Field(
        default_factory=list,
        description="性格特质列表"
    )

    # 说话风格
    speaking_style: SpeakingStyle = Field(
        default=SpeakingStyle.CASUAL,
        description="说话风格"
    )

    # 语言习惯
    catchphrases: List[str] = Field(
        default_factory=list,
        description="口头禅/常用表达"
    )

    vocabulary_level: str = Field(
        default="intermediate",
        description="词汇水平: simple/intermediate/advanced"
    )

    # 知识领域
    expertise_areas: List[str] = Field(
        default_factory=list,
        description="专业领域"
    )

    # 情绪反应模式
    emotional_responses: Dict[str, str] = Field(
        default_factory=dict,
        description="情绪反应模式: {情绪类型: 反应方式}"
    )

    # 示例对话（用于 few-shot learning）
    example_dialogues: List[ExampleDialogue] = Field(
        default_factory=list,
        description="示例对话"
    )

    # 禁忌话题
    taboo_topics: List[str] = Field(
        default_factory=list,
        description="禁忌话题"
    )

    # 特殊指令
    special_instructions: Optional[str] = Field(
        None,
        description="特殊行为指令"
    )

    def to_system_prompt(self) -> str:
        """
        将人物档案转换为系统提示词

        Returns:
            系统提示词
        """
        # 基础身份
        prompt = f"""你现在扮演 {self.name}，{self.role}。

背景故事：
{self.background}

"""

        # 性格特质
        if self.personality_traits:
            traits_str = "、".join([trait.value for trait in self.personality_traits])
            prompt += f"性格特质：{traits_str}\n\n"

        # 说话风格
        style_descriptions = {
            SpeakingStyle.CASUAL: "随意自然，像朋友聊天",
            SpeakingStyle.FORMAL: "正式礼貌，专业严谨",
            SpeakingStyle.PLAYFUL: "俏皮幽默，轻松活泼",
            SpeakingStyle.CONCISE: "简洁明了，直奔主题",
            SpeakingStyle.DETAILED: "详细全面，深入解释",
            SpeakingStyle.STORYTELLING: "善于讲故事，生动有趣"
        }
        prompt += f"说话风格：{style_descriptions.get(self.speaking_style, '自然随意')}\n\n"

        # 口头禅
        if self.catchphrases:
            phrases = "、".join(self.catchphrases)
            prompt += f"常用表达：{phrases}\n\n"

        # 专业领域
        if self.expertise_areas:
            areas = "、".join(self.expertise_areas)
            prompt += f"专业领域：{areas}\n\n"

        # 情绪反应
        if self.emotional_responses:
            prompt += "情绪反应模式：\n"
            for emotion, response in self.emotional_responses.items():
                prompt += f"- 当用户感到{emotion}时：{response}\n"
            prompt += "\n"

        # 禁忌话题
        if self.taboo_topics:
            topics = "、".join(self.taboo_topics)
            prompt += f"避免话题：{topics}\n\n"

        # 特殊指令
        if self.special_instructions:
            prompt += f"特殊要求：{self.special_instructions}\n\n"

        # 示例对话
        if self.example_dialogues:
            prompt += "对话示例：\n\n"
            for i, example in enumerate(self.example_dialogues[:5], 1):  # 最多5个示例
                prompt += f"用户：{example.user_input}\n"
                prompt += f"{self.name}：{example.response}\n\n"

        # 行为指导
        prompt += """行为指导：
1. 始终保持角色一致性，不要跳出角色
2. 根据对话上下文调整语气和情绪
3. 使用符合人物特征的表达方式
4. 对用户保持友好和帮助性
5. 如果不确定如何回应，可以表达思考过程

请用中文回复，保持自然流畅。"""

        return prompt


class ProfileManager:
    """人物档案管理器"""

    def __init__(self):
        self.profiles: Dict[str, PersonProfile] = {}

    def add_profile(self, profile: PersonProfile):
        """添加人物档案"""
        self.profiles[profile.name] = profile

    def get_profile(self, name: str) -> Optional[PersonProfile]:
        """获取人物档案"""
        return self.profiles.get(name)

    def list_profiles(self) -> List[str]:
        """列出所有人物名称"""
        return list(self.profiles.keys())

    def create_default_profiles(self):
        """创建默认人物档案"""
        # 示例：创建一个温暖的心理咨询师
        therapist = PersonProfile(
            name="小云",
            role="心理咨询师",
            background="你是一位温暖、专业的心理咨询师，有10年的咨询经验。你擅长倾听，善于共情，能够帮助用户理清思路，找到内心的答案。",
            personality_traits=[
                PersonalityTrait.WARM,
                PersonalityTrait.EMPATHETIC,
                PersonalityTrait.PROFESSIONAL
            ],
            speaking_style=SpeakingStyle.CASUAL,
            catchphrases=["我理解你的感受", "让我们一起来看看", "你觉得呢？"],
            expertise_areas=["心理咨询", "情绪管理", "人际关系", "自我成长"],
            emotional_responses={
                "焦虑": "先安抚情绪，然后帮助分析焦虑的根源",
                "沮丧": "给予共情和支持，提供积极的视角",
                "愤怒": "理解愤怒背后的需求，引导合理表达"
            },
            example_dialogues=[
                ExampleDialogue(
                    user_input="我最近感觉很焦虑",
                    response="我理解你的感受。焦虑是很正常的情绪反应。能跟我说说，是什么让你感到焦虑吗？",
                    emotion="焦虑"
                ),
                ExampleDialogue(
                    user_input="我觉得自己很失败",
                    response="听起来你现在对自己很失望。但我想告诉你，能够觉察到自己的感受，这本身就是一种勇气。让我们一起来看看，是什么让你有这样的感觉？",
                    emotion="沮丧"
                )
            ],
            special_instructions="在回应时，先表达对用户情绪的理解和接纳，然后再提供帮助。"
        )

        self.add_profile(therapist)

        # 示例：创建一个幽默的朋友
        friend = PersonProfile(
            name="小明",
            role="你的好朋友",
            background="你是小明，一个乐观、幽默、讲义气的好朋友。你喜欢开玩笑，但关键时刻很靠谱。",
            personality_traits=[
                PersonalityTrait.HUMOROUS,
                PersonalityTrait.WARM,
                PersonalityTrait.PRACTICAL
            ],
            speaking_style=SpeakingStyle.PLAYFUL,
            catchphrases=["哈哈", "没问题！", "包在我身上", "兄弟/姐妹"],
            expertise_areas=["生活经验", "娱乐", "美食", "旅行"],
            example_dialogues=[
                ExampleDialogue(
                    user_input="我今天心情不好",
                    response="哎呀，谁惹你不开心了？告诉我，我帮你出气！或者...我们去吃顿好的？"
                ),
                ExampleDialogue(
                    user_input="我遇到点麻烦",
                    response="别担心，有我在呢！说说看，咱们一起想办法。"
                )
            ]
        )

        self.add_profile(friend)
