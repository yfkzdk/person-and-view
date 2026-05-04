"""细粒度情绪类型 - 基于Plutchik情绪轮的70+种情绪定义"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

from src.emotion.emotion_dimensions import EmotionDimension


class FineEmotionType(Enum):
    """
    细粒度情绪类型枚举

    基于Plutchik的八种基本情绪及其组合:
    - Joy (喜悦): Serenity < Joy < Happiness < Ecstasy
    - Trust (信任): Acceptance < Trust < Admiration < Love
    - Fear (恐惧): Apprehension < Fear < Terror < Panic
    - Surprise (惊讶): Surprise < Amazement < Astonishment
    - Sadness (悲伤): Pensiveness < Sadness < Grief < Despair
    - Disgust (厌恶): Boredom < Disgust < Loathing < Hatred
    - Anger (愤怒): Annoyance < Anger < Rage < Fury
    - Anticipation (期待): Interest < Anticipation < Vigilance < Excitement

    每种情绪包含:
    - value: 中文标签
    - family: 情绪家族 (8种基本情绪之一)
    - intensity_level: 强度等级 (1-3, 1最弱, 3最强)
    """

    # ==================== Joy Family (喜悦家族) ====================
    SERENITY = ("平静", "joy", 1)
    JOY = ("喜悦", "joy", 1)
    HAPPINESS = ("幸福", "joy", 2)
    CHEERFULNESS = ("愉快", "joy", 2)
    DELIGHT = ("快乐", "joy", 2)
    ENTHUSIASM = ("热情", "joy", 3)
    EUPHORIA = ("亢奋", "joy", 3)
    ECSTASY = ("狂喜", "joy", 3)
    BLISS = ("极乐", "joy", 3)

    # ==================== Trust Family (信任家族) ====================
    ACCEPTANCE = ("接受", "trust", 1)
    TRUST = ("信任", "trust", 1)
    ADMIRATION = ("钦佩", "trust", 2)
    RESPECT = ("尊敬", "trust", 2)
    CONFIDENCE = ("信心", "trust", 2)
    DEVOTION = ("奉献", "trust", 3)
    REVERENCE = ("崇敬", "trust", 3)
    FAITH = ("信仰", "trust", 3)

    # ==================== Fear Family (恐惧家族) ====================
    APPREHENSION = ("忧虑", "fear", 1)
    ANXIETY = ("焦虑", "fear", 1)
    FEAR = ("恐惧", "fear", 2)
    WORRY = ("担心", "fear", 2)
    UNEASINESS = ("不安", "fear", 2)
    DREAD = ("畏惧", "fear", 3)
    TERROR = ("惊恐", "fear", 3)
    PANIC = ("恐慌", "fear", 3)
    HORROR = ("恐怖", "fear", 3)

    # ==================== Surprise Family (惊讶家族) ====================
    SURPRISE = ("惊讶", "surprise", 1)
    ASTONISHMENT = ("吃惊", "surprise", 2)
    AMAZEMENT = ("惊奇", "surprise", 2)
    WONDER = ("惊叹", "surprise", 2)
    SHOCK = ("震惊", "surprise", 3)
    STUN = ("惊呆", "surprise", 3)
    ASTOUNDMENT = ("惊骇", "surprise", 3)

    # ==================== Sadness Family (悲伤家族) ====================
    PENSIVENESS = ("忧郁", "sadness", 1)
    MELANCHOLY = ("伤感", "sadness", 1)
    SADNESS = ("悲伤", "sadness", 2)
    GLOOM = ("沮丧", "sadness", 2)
    DISAPPOINTMENT = ("失望", "sadness", 2)
    GRIEF = ("悲痛", "sadness", 3)
    DESPAIR = ("绝望", "sadness", 3)
    SORROW = ("哀伤", "sadness", 3)
    DEPRESSION = ("抑郁", "sadness", 3)

    # ==================== Disgust Family (厌恶家族) ====================
    BOREDOM = ("无聊", "disgust", 1)
    INDIFFERENCE = ("冷漠", "disgust", 1)
    DISGUST = ("厌恶", "disgust", 2)
    AVERSION = ("反感", "disgust", 2)
    DISTASTE = ("嫌弃", "disgust", 2)
    LOATHING = ("憎恶", "disgust", 3)
    REVULSION = ("恶心", "disgust", 3)
    HATRED = ("仇恨", "disgust", 3)
    ABHORRENCE = ("痛恨", "disgust", 3)

    # ==================== Anger Family (愤怒家族) ====================
    ANNOYANCE = ("烦恼", "anger", 1)
    IRRITATION = ("烦躁", "anger", 1)
    FRUSTRATION = ("挫败", "anger", 2)
    ANGER = ("愤怒", "anger", 2)
    RESENTMENT = ("怨恨", "anger", 2)
    RAGE = ("暴怒", "anger", 3)
    FURY = ("狂怒", "anger", 3)
    WRATH = ("盛怒", "anger", 3)
    OUTRAGE = ("义愤", "anger", 3)

    # ==================== Anticipation Family (期待家族) ====================
    INTEREST = ("兴趣", "anticipation", 1)
    CURIOSITY = ("好奇", "anticipation", 1)
    ANTICIPATION = ("期待", "anticipation", 2)
    EXPECTATION = ("期望", "anticipation", 2)
    HOPE = ("希望", "anticipation", 2)
    VIGILANCE = ("警觉", "anticipation", 3)
    EAGERNESS = ("渴望", "anticipation", 3)
    EXCITEMENT = ("兴奋", "anticipation", 3)

    # ==================== Neutral (中性) ====================
    NEUTRAL = ("平静", "neutral", 0)

    # ==================== Dyadic Emotions (二元情绪) ====================
    # Love = Joy + Trust
    LOVE = ("爱", "love", 2)
    AFFECTION = ("喜爱", "love", 1)
    FONDNESS = ("钟爱", "love", 2)
    ADORATION = ("热爱", "love", 3)

    # Optimism = Joy + Anticipation
    OPTIMISM = ("乐观", "optimism", 2)
    HOPEFULNESS = ("充满希望", "optimism", 2)
    ENTHUSIASM_ANTICIPATION = ("热切期待", "optimism", 3)

    # Submission = Trust + Fear
    SUBMISSION = ("顺从", "submission", 2)
    COMPLIANCE = ("服从", "submission", 1)
    RESIGNATION = ("认命", "submission", 3)

    # Awe = Fear + Surprise
    AWE = ("敬畏", "awe", 2)
    WONDER_FEAR = ("惊叹敬畏", "awe", 3)

    # Disappointment = Surprise + Sadness
    DISMAY = ("沮丧惊讶", "disappointment", 2)
    DISMAYMENT = ("惊愕失望", "disappointment", 3)

    # Remorse = Sadness + Disgust
    REMORSE = ("懊悔", "remorse", 2)
    GUILT = ("内疚", "remorse", 2)
    SHAME = ("羞愧", "remorse", 3)
    REGRET = ("遗憾", "remorse", 1)

    # Contempt = Disgust + Anger
    CONTEMPT = ("蔑视", "contempt", 2)
    SCORN = ("鄙视", "contempt", 3)
    DISDAIN = ("轻蔑", "contempt", 2)

    # Aggressiveness = Anger + Anticipation
    AGGRESSIVENESS = ("攻击性", "aggressiveness", 2)
    HOSTILITY = ("敌意", "aggressiveness", 3)

    # ==================== Additional Nuanced Emotions ====================
    # Complex emotional states
    NOSTALGIA = ("怀旧", "sadness", 1)
    LONGING = ("思念", "sadness", 2)
    YEARNING = ("渴望思念", "sadness", 2)

    RELIEF = ("释然", "joy", 2)
    CONTENTMENT = ("满足", "joy", 2)
    GRATITUDE = ("感恩", "joy", 2)

    EMBARRASSMENT = ("尴尬", "fear", 1)
    SHYNESS = ("害羞", "fear", 1)
    SELF_CONSCIOUSNESS = ("局促", "fear", 1)

    CONFUSION = ("困惑", "surprise", 1)
    PERPLEXITY = ("迷茫", "surprise", 1)

    SYMPATHY = ("同情", "sadness", 1)
    COMPASSION = ("怜悯", "sadness", 2)
    EMPATHY = ("共情", "sadness", 2)

    PRIDE = ("自豪", "joy", 2)
    TRIUMPH = ("胜利感", "joy", 3)
    SATISFACTION = ("满意", "joy", 1)

    ENVY = ("嫉妒", "anger", 2)
    JEALOUSY = ("妒忌", "anger", 3)

    SERIOUSNESS = ("严肃", "anticipation", 1)
    DETERMINATION = ("决心", "anticipation", 3)

    def __new__(cls, chinese_label: str, family: str, intensity_level: int):
        obj = object.__new__(cls)
        obj._value_ = chinese_label  # Set .value to just the Chinese label
        obj._chinese_label = chinese_label
        obj._family = family
        obj._intensity_level = intensity_level
        return obj

    def __init__(self, chinese_label: str, family: str, intensity_level: int):
        pass

    @property
    def family(self) -> str:
        """获取情绪家族"""
        return self._family

    @property
    def intensity_level(self) -> int:
        """获取情绪强度等级 (1-3)"""
        return self._intensity_level

    def to_pad(self) -> EmotionDimension:
        """
        将情绪映射到PAD三维维度

        基于Plutchik情绪轮和PAD模型的理论映射:
        - Joy: 高愉悦、高唤醒、中等支配
        - Trust: 中等愉悦、低唤醒、低支配
        - Fear: 低愉悦、高唤醒、低支配
        - Surprise: 中等愉悦、高唤醒、中等支配
        - Sadness: 低愉悦、低唤醒、低支配
        - Disgust: 低愉悦、低唤醒、中等支配
        - Anger: 低愉悦、高唤醒、高支配
        - Anticipation: 中等愉悦、中等唤醒、高支配
        """
        # 基础PAD映射表 (pleasure, arousal, dominance)
        base_pad: Dict[str, Tuple[float, float, float]] = {
            "joy": (0.7, 0.5, 0.3),
            "trust": (0.4, -0.2, -0.3),
            "fear": (-0.6, 0.6, -0.5),
            "surprise": (0.2, 0.8, 0.0),
            "sadness": (-0.7, -0.4, -0.4),
            "disgust": (-0.5, -0.1, 0.2),
            "anger": (-0.6, 0.7, 0.6),
            "anticipation": (0.3, 0.3, 0.5),
            # 二元情绪
            "love": (0.8, 0.4, 0.0),
            "optimism": (0.6, 0.5, 0.4),
            "submission": (-0.2, 0.0, -0.6),
            "awe": (0.0, 0.7, -0.3),
            "disappointment": (-0.4, 0.2, -0.2),
            "remorse": (-0.5, -0.3, -0.4),
            "contempt": (-0.4, 0.3, 0.4),
            "aggressiveness": (-0.3, 0.6, 0.7),
        }

        # 获取基础PAD值
        base_p, base_a, base_d = base_pad.get(
            self._family, (0.0, 0.0, 0.0)
        )

        # 根据强度调整
        intensity_factor = 0.3 + (self._intensity_level - 1) * 0.35  # 0.3, 0.65, 1.0

        # 计算最终PAD值
        pleasure = max(-1.0, min(1.0, base_p * intensity_factor * 1.2))
        arousal = max(-1.0, min(1.0, base_a * intensity_factor * 1.2))
        dominance = max(-1.0, min(1.0, base_d * intensity_factor * 1.2))

        return EmotionDimension(
            pleasure=pleasure,
            arousal=arousal,
            dominance=dominance
        )


@dataclass
class RichEmotionState:
    """
    丰富的情绪状态表示

    结合情绪类型与PAD维度，提供更完整的情绪描述。

    Attributes:
        primary_emotion: 主要情绪类型
        intensity: 情绪强度 (0.0-1.0)
        confidence: 识别置信度 (0.0-1.0)
        pad_dimensions: PAD三维情绪维度
        secondary_emotions: 次要情绪列表，每个元素为(情绪类型, 强度)元组
    """

    primary_emotion: FineEmotionType
    intensity: float
    confidence: float
    pad_dimensions: EmotionDimension
    secondary_emotions: Optional[Dict[FineEmotionType, float]] = None

    def __post_init__(self):
        """验证字段值范围"""
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(
                f"intensity must be between 0.0 and 1.0, got {self.intensity}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def to_dict(self) -> Dict:
        """转换为字典表示"""
        return {
            'primary_emotion': self.primary_emotion.value,
            'intensity': self.intensity,
            'confidence': self.confidence,
            'pad_dimensions': self.pad_dimensions.to_dict(),
            'secondary_emotions': (
                {e.value: s for e, s in self.secondary_emotions.items()}
                if self.secondary_emotions else None
            )
        }


class FineGrainedEmotionAnalyzer(nn.Module):
    """
    细粒度情绪分析器

    使用Chinese-BERT-wwm进行细粒度情绪识别
    """

    # 情绪关键词映射（用于fallback）
    EMOTION_KEYWORDS = {
        # Joy family
        'SERENITY': ['平静', '安宁', '宁静'],
        'JOY': ['开心', '高兴', '快乐', '喜悦'],
        'ECSTASY': ['狂喜', '欣喜若狂', '太棒了'],

        # Sadness family
        'PENSIVENESS': ['沉思', '若有所思'],
        'SADNESS': ['悲伤', '难过', '伤心', '失落'],
        'GRIEF': ['悲痛', '痛心', '心碎'],

        # Anger family
        'ANNOYANCE': ['有点烦', '不太爽'],
        'ANGER': ['愤怒', '生气', '恼火'],
        'RAGE': ['暴怒', '气炸了', '火冒三丈'],

        # Fear family
        'APPREHENSION': ['担心', '忧虑'],
        'FEAR': ['恐惧', '害怕', '惊恐'],
        'TERROR': ['吓坏了', '魂飞魄散'],

        # Surprise family
        'SURPRISE': ['惊讶', '意外', '没想到'],
        'AMAZEMENT': ['震惊', '不可思议'],

        # Additional emotions
        'ANXIETY': ['焦虑', '紧张', '不安'],
        'DEPRESSION': ['抑郁', '沮丧', '消沉'],
        'EXCITEMENT': ['兴奋', '激动', '期待'],
        'GRATITUDE': ['感激', '感谢', '感恩'],
        'LOVE': ['爱', '喜欢', '喜爱'],
        'DISAPPOINTMENT': ['失望', '遗憾'],
        'FRUSTRATION': ['挫败', '受挫', '沮丧'],
        'NEUTRAL': ['平静', '一般', '还好']
    }

    def __init__(self, model_name: str = "hfl/chinese-roberta-wwm-ext"):
        super().__init__()

        # 尝试加载BERT模型 (use local_files_only to avoid network timeouts)
        try:
            self.bert = AutoModel.from_pretrained(model_name, local_files_only=True)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
            self.use_fallback = False
        except Exception as e:
            logger.warning(f"BERT model not found locally ({model_name}), using keyword fallback: {e}")
            self.bert = None
            self.tokenizer = None
            self.use_fallback = True

        # 细粒度情绪分类器 (70+ 类别)
        num_emotions = len(FineEmotionType)
        self.emotion_classifier = nn.Sequential(
            nn.Linear(768, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_emotions)
        )

        # 强度回归器
        self.intensity_regressor = nn.Sequential(
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        """前向传播"""
        if self.use_fallback:
            batch_size = input_ids.shape[0]
            num_emotions = len(FineEmotionType)
            emotion_logits = torch.randn(batch_size, num_emotions)
            intensity = torch.rand(batch_size, 1)
            return emotion_logits, intensity

        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output

        emotion_logits = self.emotion_classifier(pooled_output)
        intensity = self.intensity_regressor(pooled_output)

        return emotion_logits, intensity

    def analyze(self, text: str) -> RichEmotionState:
        """
        分析文本情绪

        Args:
            text: 输入文本

        Returns:
            RichEmotionState: 丰富情绪状态
        """
        # 空输入处理
        if not text or not text.strip():
            return RichEmotionState(
                primary_emotion=FineEmotionType.NEUTRAL,
                intensity=0.0,
                confidence=1.0,
                pad_dimensions=FineEmotionType.NEUTRAL.to_pad()
            )

        # Fallback模式：关键词匹配
        if self.use_fallback:
            return self._fallback_analyze(text)

        # BERT模式
        return self._bert_analyze(text)

    def _fallback_analyze(self, text: str) -> RichEmotionState:
        """Fallback分析：关键词匹配"""
        detected_emotion = FineEmotionType.NEUTRAL
        max_matches = 0

        for emotion_name, keywords in self.EMOTION_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > max_matches:
                max_matches = matches
                detected_emotion = FineEmotionType[emotion_name]

        # 估算强度（基于关键词数量和强度词）
        intensity = 0.5
        if any(word in text for word in ['非常', '特别', '极其', '太', '简直', '超级', '十分']):
            intensity = 0.8
        elif any(word in text for word in ['有点', '稍微', '一些', '一点']):
            intensity = 0.3

        return RichEmotionState(
            primary_emotion=detected_emotion,
            intensity=intensity,
            confidence=0.6 if max_matches > 0 else 0.3,
            pad_dimensions=detected_emotion.to_pad()
        )

    def _bert_analyze(self, text: str) -> RichEmotionState:
        """BERT模型分析"""
        # 编码文本
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )

        # 推理
        with torch.no_grad():
            emotion_logits, intensity = self.forward(
                inputs['input_ids'],
                inputs['attention_mask']
            )

        # 获取主要情绪
        probs = torch.softmax(emotion_logits, dim=-1)
        emotion_idx = torch.argmax(probs, dim=-1).item()
        confidence = probs[0, emotion_idx].item()

        # 获取情绪类型
        emotion_types = list(FineEmotionType)
        primary_emotion = emotion_types[emotion_idx]

        # 获取次要情绪
        secondary_emotions = {}
        for i, prob in enumerate(probs[0].tolist()):
            if i != emotion_idx and prob > 0.05:  # 阈值
                secondary_emotions[emotion_types[i]] = prob

        return RichEmotionState(
            primary_emotion=primary_emotion,
            intensity=intensity.item(),
            confidence=confidence,
            pad_dimensions=primary_emotion.to_pad(),
            secondary_emotions=secondary_emotions if secondary_emotions else None
        )
