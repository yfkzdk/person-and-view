"""
角色卡片系统 - 参考SillyTavern的角色定义格式
支持导入/导出角色卡片，实现角色共享
"""
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class CharacterCard(BaseModel):
    """
    角色卡片 - 兼容SillyTavern格式

    参考项目：SillyTavern (https://github.com/SillyTavern/SillyTavern)
    """

    # 基本信息
    name: str = Field(..., description="角色名称")
    description: str = Field("", description="角色描述")

    # 人格定义
    personality: str = Field("", description="性格描述")
    scenario: str = Field("", description="场景设定")
    first_mes: str = Field("", description="第一条消息")
    mes_example: str = Field("", description="对话示例")

    # 系统提示词（核心）
    system_prompt: str = Field("", description="系统提示词")

    # 扩展字段
    creator: str = Field("", description="创建者")
    character_version: str = Field("1.0", description="角色版本")
    tags: List[str] = Field(default_factory=list, description="标签")

    # 元数据
    spec: str = Field("chara_card_v2", description="卡片规格")
    spec_version: str = Field("2.0", description="规格版本")

    # 扩展数据
    extensions: Dict = Field(default_factory=dict, description="扩展数据")

    # 我们的自定义字段
    custom_fields: Dict = Field(
        default_factory=dict,
        description="自定义字段：情绪反应、知识领域等"
    )

    def to_sillytavern_format(self) -> Dict:
        """转换为SillyTavern兼容格式"""
        return {
            "spec": self.spec,
            "spec_version": self.spec_version,
            "data": {
                "name": self.name,
                "description": self.description,
                "personality": self.personality,
                "scenario": self.scenario,
                "first_mes": self.first_mes,
                "mes_example": self.mes_example,
                "system_prompt": self.system_prompt,
                "creator": self.creator,
                "character_version": self.character_version,
                "tags": self.tags,
                "extensions": self.extensions
            }
        }

    @classmethod
    def from_sillytavern_format(cls, data: Dict) -> "CharacterCard":
        """从SillyTavern格式导入"""
        if "data" in data:
            # v2格式
            card_data = data["data"]
            return cls(
                spec=data.get("spec", "chara_card_v2"),
                spec_version=data.get("spec_version", "2.0"),
                **card_data
            )
        else:
            # v1格式
            return cls(**data)

    def to_system_prompt(self) -> str:
        """
        生成完整的系统提示词

        Returns:
            系统提示词
        """
        # 如果system_prompt已经是完整的（包含角色扮演规则等），直接使用
        if self.system_prompt and len(self.system_prompt) > 500:
            # 检查是否包含完整的角色定义结构
            if any(keyword in self.system_prompt for keyword in ["角色扮演规则", "## ", "---", "身份卡"]):
                # 已经是完整的系统提示词，直接返回
                return self.system_prompt

        prompt_parts = []

        # 基础身份
        prompt_parts.append(f"你现在扮演 {self.name}。")

        # 描述
        if self.description:
            prompt_parts.append(f"\n{self.description}")

        # 性格
        if self.personality:
            prompt_parts.append(f"\n\n性格特点：{self.personality}")

        # 场景
        if self.scenario:
            prompt_parts.append(f"\n\n场景设定：{self.scenario}")

        # 系统提示词（如果有自定义的）
        if self.system_prompt:
            prompt_parts.append(f"\n\n{self.system_prompt}")

        # 自定义字段
        if self.custom_fields:
            # 情绪反应
            if "emotional_responses" in self.custom_fields:
                prompt_parts.append("\n\n情绪反应模式：")
                for emotion, response in self.custom_fields["emotional_responses"].items():
                    prompt_parts.append(f"- 当用户感到{emotion}时：{response}")

            # 知识领域
            if "expertise_areas" in self.custom_fields:
                areas = "、".join(self.custom_fields["expertise_areas"])
                prompt_parts.append(f"\n\n专业领域：{areas}")

            # 说话风格
            if "speaking_style" in self.custom_fields:
                prompt_parts.append(f"\n\n说话风格：{self.custom_fields['speaking_style']}")

            # 口头禅
            if "catchphrases" in self.custom_fields:
                phrases = "、".join(self.custom_fields["catchphrases"])
                prompt_parts.append(f"\n\n常用表达：{phrases}")

        # 对话示例
        if self.mes_example:
            prompt_parts.append(f"\n\n对话示例：\n{self.mes_example}")

        # 行为指导
        prompt_parts.append("""

行为指导：
1. 始终保持角色一致性，不要跳出角色
2. 根据对话上下文调整语气和情绪
3. 使用符合人物特征的表达方式
4. 对用户保持友好和帮助性
5. 如果不确定如何回应，可以表达思考过程

请用中文回复，保持自然流畅。""")

        return "\n".join(prompt_parts)

    def export_to_file(self, filepath: str):
        """导出角色卡片到文件"""
        data = self.to_sillytavern_format()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def import_from_file(cls, filepath: str) -> "CharacterCard":
        """从文件导入角色卡片"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_sillytavern_format(data)


class CharacterCardManager:
    """角色卡片管理器"""

    def __init__(self, cards_dir: str = "characters"):
        """
        初始化管理器

        Args:
            cards_dir: 角色卡片存储目录
        """
        self.cards_dir = cards_dir
        self.cards: Dict[str, CharacterCard] = {}
        self.active_card: Optional[CharacterCard] = None

    def create_card(
        self,
        name: str,
        description: str = "",
        personality: str = "",
        **kwargs
    ) -> CharacterCard:
        """
        创建新角色卡片

        Args:
            name: 角色名称
            description: 角色描述
            personality: 性格描述

        Returns:
            角色卡片
        """
        card = CharacterCard(
            name=name,
            description=description,
            personality=personality,
            **kwargs
        )

        self.cards[name] = card
        return card

    def get_card(self, name: str) -> Optional[CharacterCard]:
        """获取角色卡片"""
        return self.cards.get(name)

    def list_cards(self) -> List[str]:
        """列出所有角色名称"""
        return list(self.cards.keys())

    def set_active_card(self, name: str) -> bool:
        """设置当前激活的角色"""
        if name in self.cards:
            self.active_card = self.cards[name]
            return True
        return False

    def save_card(self, name: str, filepath: Optional[str] = None):
        """保存角色卡片"""
        if name not in self.cards:
            raise ValueError(f"Card not found: {name}")

        card = self.cards[name]

        if filepath is None:
            import os
            os.makedirs(self.cards_dir, exist_ok=True)
            filepath = f"{self.cards_dir}/{name}.json"

        card.export_to_file(filepath)

    def load_card(self, filepath: str) -> CharacterCard:
        """加载角色卡片"""
        card = CharacterCard.import_from_file(filepath)
        self.cards[card.name] = card
        return card

    def load_all_cards(self):
        """从cards_dir加载所有角色卡片"""
        import os as _os

        # 加载 JSON 格式
        if _os.path.exists(self.cards_dir):
            for filename in _os.listdir(self.cards_dir):
                if filename.endswith('.json'):
                    filepath = _os.path.join(self.cards_dir, filename)
                    try:
                        self.load_card(filepath)
                    except Exception as e:
                        print(f"Warning: Failed to load {filepath}: {e}")

    def load_card_from_yaml(self, filepath: str) -> "CharacterCard":
        """从 YAML 文件加载角色卡片"""
        import os
        import yaml
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty YAML: {filepath}")

        name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])

        # 构建 CharacterCard
        sample_dialogues = data.get("sample_dialogues", [])
        mes_example = ""
        if sample_dialogues:
            examples = []
            for d in sample_dialogues:
                user_msg = d.get("user", "")
                asst_msg = d.get("assistant", "")
                examples.append(f"{{{{user}}}}: {user_msg}\n{{{{char}}}}: {asst_msg}")
            mes_example = "\n\n".join(examples)

        card = CharacterCard(
            name=name,
            description=data.get("description", ""),
            personality=data.get("personality", ""),
            scenario=data.get("scenario", ""),
            first_mes=data.get("greeting", data.get("first_mes", "")),
            mes_example=mes_example,
            system_prompt=data.get("system_prompt", data.get("personality", "")),
            creator=data.get("creator", "YAML Import"),
            tags=data.get("tags", []),
            custom_fields={
                "voice": data.get("voice", ""),
                "language": data.get("language", "zh-CN"),
                "emotional_responses": data.get("emotional_responses", {}),
                "catchphrases": data.get("catchphrases", []),
            }
        )

        self.cards[card.name] = card
        return card

    def create_default_characters(self):
        """创建默认角色，并加载已有角色"""

        # 先加载已有角色
        self.load_all_cards()

        # 如果没有角色，创建默认角色
        if not self.cards:
            # 1. 心理咨询师
            therapist = self.create_card(
            name="小云",
            description="一位温暖、专业的心理咨询师，有10年的咨询经验。擅长倾听，善于共情，能够帮助用户理清思路，找到内心的答案。",
            personality="温暖、同理心强、专业、耐心",
            scenario="心理咨询室",
            first_mes="你好，我是小云。很高兴见到你，有什么我可以帮助你的吗？",
            mes_example="<START>\n{{user}}: 我最近感觉很焦虑\n{{char}}: 我理解你的感受。焦虑是很正常的情绪反应。能跟我说说，是什么让你感到焦虑吗？\n\n<START>\n{{user}}: 我觉得自己很失败\n{{char}}: 听起来你现在对自己很失望。但我想告诉你，能够觉察到自己的感受，这本身就是一种勇气。",
            system_prompt="你是一位专业的心理咨询师，擅长倾听和共情。",
            creator="System",
            tags=["心理咨询", "温暖", "专业"],
            custom_fields={
                "emotional_responses": {
                    "焦虑": "先安抚情绪，然后帮助分析焦虑的根源",
                    "沮丧": "给予共情和支持，提供积极的视角",
                    "愤怒": "理解愤怒背后的需求，引导合理表达"
                },
                "expertise_areas": ["心理咨询", "情绪管理", "人际关系", "自我成长"],
                "speaking_style": "温暖自然，像朋友聊天",
                "catchphrases": ["我理解你的感受", "让我们一起来看看", "你觉得呢？"]
            }
        )

            # 2. 幽默朋友
            friend = self.create_card(
            name="小明",
            description="一个乐观、幽默、讲义气的好朋友。喜欢开玩笑，但关键时刻很靠谱。",
            personality="幽默、乐观、讲义气、随和",
            scenario="日常生活",
            first_mes="嘿！好久不见啊，最近怎么样？",
            mes_example="<START>\n{{user}}: 我今天心情不好\n{{char}}: 哎呀，谁惹你不开心了？告诉我，我帮你出气！或者...我们去吃顿好的？\n\n<START>\n{{user}}: 我遇到点麻烦\n{{char}}: 别担心，有我在呢！说说看，咱们一起想办法。",
            system_prompt="你是一个幽默风趣的好朋友，善于活跃气氛。",
            creator="System",
            tags=["朋友", "幽默", "乐观"],
            custom_fields={
                "expertise_areas": ["生活经验", "娱乐", "美食", "旅行"],
                "speaking_style": "随意自然，喜欢开玩笑",
                "catchphrases": ["哈哈", "没问题！", "包在我身上"]
            }
        )

            # 3. 理性分析师
            analyst = self.create_card(
            name="分析师",
            description="一位善于理性分析、逻辑思考的顾问。擅长从多个角度分析问题，提供客观的建议。",
            personality="理性、严谨、善于分析、客观",
            scenario="咨询会议",
            first_mes="你好，我是你的分析顾问。有什么问题需要我帮你分析吗？",
            mes_example="<START>\n{{user}}: 我遇到一个问题\n{{char}}: 让我来帮你分析一下。首先，我们需要理清思路，看看问题的核心是什么。\n\n<START>\n{{user}}: 这个方案可行吗？\n{{char}}: 从实际角度来看，这个方案有一定的可行性。不过，我们需要考虑几个关键因素...",
            system_prompt="你是一位理性的分析师，擅长逻辑思考和问题分析。",
            creator="System",
            tags=["分析", "理性", "专业"],
            custom_fields={
                "expertise_areas": ["数据分析", "逻辑推理", "决策支持"],
                "speaking_style": "严谨专业，条理清晰",
                "catchphrases": ["让我来分析一下", "从...角度来看", "基于我的分析"]
            }
        )

            return [therapist, friend, analyst]

        return list(self.cards.values())


# 使用示例
if __name__ == "__main__":
    # 创建管理器
    manager = CharacterCardManager()
    manager.create_default_characters()

    # 导出角色卡片
    manager.save_card("小云")
    manager.save_card("小明")
    manager.save_card("分析师")

    print("✅ 已创建3个默认角色卡片")
    print(f"角色列表: {manager.list_cards()}")

    # 查看系统提示词
    xiaoyun = manager.get_card("小云")
    print("\n" + "=" * 80)
    print("小云的系统提示词：")
    print("=" * 80)
    print(xiaoyun.to_system_prompt())
