"""
情绪感知对话系统 - 集成情绪分析到对话流程

功能：
- 实时检测用户情绪
- 根据情绪调整回复策略
- 结合角色特征生成情绪化回复
"""
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import re


class EmotionState(BaseModel):
    """情绪状态"""
    primary_emotion: str = Field(..., description="主要情绪")
    intensity: float = Field(0.5, ge=0.0, le=1.0, description="情绪强度")
    secondary_emotions: List[str] = Field(default_factory=list, description="次要情绪")
    confidence: float = Field(0.7, ge=0.0, le=1.0, description="置信度")


class EmotionAnalyzer:
    """
    情绪分析器 - 基于规则和关键词

    可以替换为更复杂的模型（如BERT情绪分类）
    """

    def __init__(self):
        """初始化情绪分析器"""
        # 情绪关键词词典
        self.emotion_keywords = {
            "开心": ["开心", "高兴", "快乐", "兴奋", "满足", "幸福", "愉快", "欣喜"],
            "悲伤": ["悲伤", "难过", "伤心", "失落", "沮丧", "痛苦", "忧郁", "哀伤"],
            "愤怒": ["愤怒", "生气", "恼火", "烦躁", "不满", "气愤", "恼怒", "暴怒"],
            "焦虑": ["焦虑", "担心", "紧张", "不安", "害怕", "恐惧", "忧虑", "惶恐"],
            "困惑": ["困惑", "迷茫", "不解", "疑惑", "搞不懂", "不明白", "糊涂"],
            "惊讶": ["惊讶", "吃惊", "意外", "震惊", "没想到", "竟然"],
            "厌恶": ["厌恶", "讨厌", "反感", "憎恨", "厌烦", "嫌弃"],
            "期待": ["期待", "盼望", "希望", "渴望", "向往", "憧憬"]
        }

        # 情绪强度修饰词
        self.intensifiers = {
            "非常": 0.9,
            "很": 0.7,
            "比较": 0.6,
            "有点": 0.4,
            "稍微": 0.3
        }

        # 否定词
        self.negators = ["不", "没", "无", "非"]

    def analyze(self, text: str) -> EmotionState:
        """
        分析文本情绪

        Args:
            text: 输入文本

        Returns:
            情绪状态
        """
        # 检测情绪
        emotion_scores = {}

        for emotion, keywords in self.emotion_keywords.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text:
                    # 基础分数
                    base_score = 0.5

                    # 检查强度修饰词
                    for intensifier, multiplier in self.intensifiers.items():
                        if intensifier + keyword in text:
                            base_score = multiplier
                            break

                    # 检查否定词
                    for negator in self.negators:
                        if negator + keyword in text:
                            base_score *= -1
                            break

                    score = max(score, base_score)

            if score > 0:
                emotion_scores[emotion] = score

        # 确定主要情绪
        if not emotion_scores:
            # 默认中性情绪
            return EmotionState(
                primary_emotion="中性",
                intensity=0.3,
                secondary_emotions=[],
                confidence=0.5
            )

        # 排序
        sorted_emotions = sorted(
            emotion_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        primary_emotion = sorted_emotions[0][0]
        intensity = sorted_emotions[0][1]
        secondary_emotions = [e[0] for e in sorted_emotions[1:3]]

        return EmotionState(
            primary_emotion=primary_emotion,
            intensity=intensity,
            secondary_emotions=secondary_emotions,
            confidence=0.7
        )


class EmotionAwareResponder:
    """
    Emotion-aware response generator with LLM-backed multi-dimensional analysis.

    Uses the LLM to extract emotion weight vectors (happy/calm/sad/angry/excited/tense)
    instead of keyword matching, eliminating "我开心不起来" → "开心" false positives.
    """

    EMOTION_PROMPT = """分析以下用户消息的情绪构成，输出纯JSON权重向量（和为1）。

情绪维度: happy(开心), calm(平静), sad(悲伤), angry(愤怒), excited(兴奋), tense(紧张/焦虑), neutral(中性)

规则:
- 混合情绪用多维度表达，如"既期待又怕"≈excited:0.4+tense:0.5
- 否定句式会翻转情绪，如"我开心不起来"情绪不是happy
- 反讽/阴阳怪气要识别真实情绪
- 中性或日常寒喧neutral权重接近1

只输出JSON，不要任何解释:
{{"happy":0.0,"calm":0.3,"sad":0.0,"angry":0.0,"excited":0.0,"tense":0.0,"neutral":0.7}}

用户消息: {user_input}"""

    def __init__(self, character_card, llm_client=None):
        self.character = character_card
        self.emotion_analyzer = EmotionAnalyzer()
        self.llm_client = llm_client  # DeepSeekClient for LLM-based analysis

        self.default_emotion_responses = {
            "开心": "分享快乐，表达祝贺",
            "悲伤": "表达同情，提供支持",
            "愤怒": "理解愤怒，帮助疏导",
            "焦虑": "安抚情绪，提供安全感",
            "困惑": "耐心解释，提供帮助",
            "惊讶": "分享惊讶，探讨原因",
            "厌恶": "理解感受，提供替代方案",
            "期待": "积极回应，共同期待"
        }

    async def analyze_emotion_weights(self, user_input: str) -> dict:
        """
        LLM-based multi-dimensional emotion analysis.
        Falls back to keyword matching if LLM client unavailable or fails.
        """
        if self.llm_client:
            try:
                prompt = self.EMOTION_PROMPT.format(user_input=user_input)
                messages = [{"role": "user", "content": prompt}]
                weights = await self.llm_client.chat_json(messages)
                # Normalize to ensure sum ≈ 1
                total = sum(weights.values())
                if total > 0:
                    weights = {k: round(v / total, 3) for k, v in weights.items()}
                # Ensure all dimensions present
                for dim in ["happy", "calm", "sad", "angry", "excited", "tense", "neutral"]:
                    weights.setdefault(dim, 0.0)
                return weights
            except Exception:
                pass  # Fall through to keyword fallback

        # Keyword fallback
        state = self.emotion_analyzer.analyze(user_input)
        return self._state_to_weights(state)

    def _state_to_weights(self, state: EmotionState) -> dict:
        """Convert single-label EmotionState to weight vector."""
        weights = {"happy": 0.0, "calm": 0.0, "sad": 0.0, "angry": 0.0,
                   "excited": 0.0, "tense": 0.0, "neutral": 0.0}
        emotion_map = {
            "开心": "happy", "高兴": "happy",
            "悲伤": "sad", "难过": "sad", "沮丧": "sad",
            "愤怒": "angry", "生气": "angry",
            "焦虑": "tense", "紧张": "tense", "害怕": "tense",
            "惊讶": "excited", "期待": "excited",
            "中性": "neutral", "困惑": "neutral",
        }
        primary = emotion_map.get(state.primary_emotion, "neutral")
        weights[primary] = state.intensity
        remaining = 1.0 - state.intensity
        weights["neutral"] = max(0, remaining)
        return weights

    def analyze_user_emotion(self, user_input: str) -> EmotionState:
        """Legacy keyword-based analysis (kept for fallback)."""
        return self.emotion_analyzer.analyze(user_input)

    def get_emotion_aware_prompt(
        self,
        user_input: str,
        emotion_state: Optional[EmotionState] = None
    ) -> str:
        """
        Build emotion-aware prompt.

        Returns a LIGHTWEIGHT block to append to the user message,
        NOT a replacement for the entire character system prompt.
        """
        if emotion_state is None:
            emotion_state = self.analyze_user_emotion(user_input)

        parts = []
        parts.append(f"[用户当前情绪: {emotion_state.primary_emotion}，强度: {emotion_state.intensity:.1%}")

        if emotion_state.secondary_emotions:
            parts.append(f"，次要情绪: {', '.join(emotion_state.secondary_emotions)}")

        parts.append("]")

        # Brief strategy hint
        character_emotion_responses = self.character.custom_fields.get(
            "emotional_responses", {}
        )
        if emotion_state.primary_emotion in character_emotion_responses:
            strategy = character_emotion_responses[emotion_state.primary_emotion]
        else:
            strategy = self.default_emotion_responses.get(
                emotion_state.primary_emotion, "自然回应"
            )
        parts.append(f" [策略: {strategy}]")

        if emotion_state.intensity > 0.7:
            parts.append(" [注意: 用户情绪强烈，需要更多共情]")

        return "".join(parts)

    def should_express_emotion(
        self,
        emotion_state: EmotionState
    ) -> Tuple[bool, Optional[str]]:
        if emotion_state.intensity > 0.6:
            return True, f"用户情绪较为强烈（{emotion_state.primary_emotion}），请在回复中体现对这种情绪的理解和关注。"
        negative_emotions = ["悲伤", "愤怒", "焦虑", "困惑"]
        if emotion_state.primary_emotion in negative_emotions:
            return True, f"用户感到{emotion_state.primary_emotion}，请在回复中给予适当的支持和帮助。"
        return False, None


# 使用示例
if __name__ == "__main__":
    from src.models.character_card import CharacterCardManager

    # 创建角色
    manager = CharacterCardManager()
    manager.create_default_characters()
    xiaoyun = manager.get_card("小云")

    # 创建情绪感知回复器
    responder = EmotionAwareResponder(xiaoyun)

    # 测试情绪分析
    test_inputs = [
        "我今天特别开心！",
        "我最近感觉很焦虑，不知道该怎么办",
        "我对这个结果很失望",
        "我有点困惑，不太明白"
    ]

    print("=" * 80)
    print("情绪分析测试")
    print("=" * 80)

    for user_input in test_inputs:
        print(f"\n用户输入: {user_input}")

        # 分析情绪
        emotion = responder.analyze_user_emotion(user_input)
        print(f"检测结果: {emotion.primary_emotion} (强度: {emotion.intensity:.1%})")

        # 判断是否需要情绪回应
        should_respond, emotion_hint = responder.should_express_emotion(emotion)
        if should_respond:
            print(f"建议: {emotion_hint}")

    print("\n" + "=" * 80)
    print("✅ 情绪感知系统测试完成")
