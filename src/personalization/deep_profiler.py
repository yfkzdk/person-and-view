"""
深度学习用户画像引擎 - 企业级实现
"""
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VoicePreferences:
    """声音偏好"""
    timbre_weights: torch.Tensor  # 音色混合权重
    speed: float  # 语速 0.5-2.0
    pitch: float  # 音调 -50 到 50
    emotion_intensities: torch.Tensor  # 情感强度


@dataclass
class LanguagePreferences:
    """语言风格偏好"""
    formality: float  # 正式度 0.0-1.0
    humor: float  # 幽默度 0.0-1.0
    detail: float  # 细节度 0.0-1.0
    emotion_expression: float  # 情感表达 0.0-1.0


@dataclass
class InteractionPreferences:
    """交互模式偏好"""
    response_length: float  # 响应长度偏好
    preferred_role: str  # 偏好角色
    emotional_sensitivity: float  # 情感敏感度


@dataclass
class DeepUserProfile:
    """深度用户画像"""
    user_id: str
    embedding: torch.Tensor
    voice_preferences: VoicePreferences
    language_preferences: LanguagePreferences
    interaction_preferences: InteractionPreferences
    confidence: float
    version: int = 1
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class VoicePreferenceNetwork(nn.Module):
    """声音偏好预测网络"""

    def __init__(self, input_dim: int = 256):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32)
        )

        # 输出层
        self.timbre_head = nn.Linear(32, 10)  # 10种音色混合权重
        self.speed_head = nn.Linear(32, 1)    # 语速
        self.pitch_head = nn.Linear(32, 1)    # 音调
        self.emotion_head = nn.Linear(32, 8)  # 8种情感强度

    def forward(self, profile_embedding: torch.Tensor) -> VoicePreferences:
        features = self.network(profile_embedding)

        return VoicePreferences(
            timbre_weights=torch.softmax(self.timbre_head(features), dim=-1),
            speed=torch.sigmoid(self.speed_head(features)) * 1.5 + 0.5,
            pitch=torch.tanh(self.pitch_head(features)) * 50,
            emotion_intensities=torch.softmax(self.emotion_head(features), dim=-1)
        )


class LanguageStyleNetwork(nn.Module):
    """语言风格预测网络"""

    def __init__(self, input_dim: int = 256):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 20)
        )

        # 输出层
        self.formality_head = nn.Linear(20, 1)
        self.humor_head = nn.Linear(20, 1)
        self.detail_head = nn.Linear(20, 1)
        self.emotion_expression_head = nn.Linear(20, 1)

    def forward(self, profile_embedding: torch.Tensor) -> LanguagePreferences:
        features = self.network(profile_embedding)

        return LanguagePreferences(
            formality=torch.sigmoid(self.formality_head(features)).item(),
            humor=torch.sigmoid(self.humor_head(features)).item(),
            detail=torch.sigmoid(self.detail_head(features)).item(),
            emotion_expression=torch.sigmoid(self.emotion_expression_head(features)).item()
        )


class InteractionPatternNetwork(nn.Module):
    """交互模式预测网络"""

    def __init__(self, input_dim: int = 256):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32)
        )

        # 输出层
        self.response_length_head = nn.Linear(32, 1)
        self.role_head = nn.Linear(32, 5)  # 5种角色
        self.sensitivity_head = nn.Linear(32, 1)

        self.role_names = ["storyteller", "mentor", "companion", "expert", "friend"]

    def forward(self, profile_embedding: torch.Tensor) -> InteractionPreferences:
        features = self.network(profile_embedding)

        role_probs = torch.softmax(self.role_head(features), dim=-1)
        preferred_role = self.role_names[torch.argmax(role_probs).item()]

        return InteractionPreferences(
            response_length=torch.sigmoid(self.response_length_head(features)).item(),
            preferred_role=preferred_role,
            emotional_sensitivity=torch.sigmoid(self.sensitivity_head(features)).item()
        )


class DeepUserProfiler(nn.Module):
    """深度学习用户画像引擎"""

    def __init__(
        self,
        model_name: str = "bert-base-chinese",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        super().__init__()

        self.device = device
        logger.info(f"Initializing DeepUserProfiler on {device}")

        # 多模态编码器
        try:
            self.text_encoder = AutoModel.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            logger.info(f"Loaded text encoder: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load {model_name}, using dummy encoder: {e}")
            self.text_encoder = None
            self.tokenizer = None

        # 用户画像生成网络
        self.profile_generator = nn.Sequential(
            nn.Linear(768, 1024),  # BERT-base hidden size = 768
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Linear(512, 256)
        )

        # 偏好预测器
        self.voice_predictor = VoicePreferenceNetwork()
        self.language_predictor = LanguageStyleNetwork()
        self.interaction_predictor = InteractionPatternNetwork()

        self.to(device)

    def encode_text(self, text: str) -> torch.Tensor:
        """编码文本"""
        if self.text_encoder is None or self.tokenizer is None:
            # 返回随机向量（用于测试）
            return torch.randn(1, 768).to(self.device)

        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(self.device)

            with torch.no_grad():
                outputs = self.text_encoder(**inputs)
                # 使用[CLS] token的输出作为文本表示
                text_embedding = outputs.last_hidden_state[:, 0, :]

            return text_embedding
        except Exception as e:
            logger.error(f"Text encoding failed: {e}")
            return torch.randn(1, 768).to(self.device)

    def forward(
        self,
        text_history: List[str],
        user_id: str
    ) -> DeepUserProfile:
        """生成深度用户画像"""

        # 1. 编码文本历史
        if text_history:
            # 编码所有历史文本
            text_embeddings = []
            for text in text_history[-10:]:  # 最多使用最近10条
                emb = self.encode_text(text)
                text_embeddings.append(emb)

            # 平均池化
            text_embedding = torch.stack(text_embeddings).mean(dim=0)
        else:
            # 没有历史，使用零向量
            text_embedding = torch.zeros(1, 768).to(self.device)

        # 2. 生成画像向量
        profile_embedding = self.profile_generator(text_embedding)

        # 3. 预测各项偏好
        voice_prefs = self.voice_predictor(profile_embedding)
        language_prefs = self.language_predictor(profile_embedding)
        interaction_prefs = self.interaction_predictor(profile_embedding)

        # 4. 计算置信度
        confidence = torch.sigmoid(torch.norm(profile_embedding)).item()

        return DeepUserProfile(
            user_id=user_id,
            embedding=profile_embedding.detach(),
            voice_preferences=voice_prefs,
            language_preferences=language_prefs,
            interaction_preferences=interaction_prefs,
            confidence=min(confidence, 1.0)
        )

    def update_profile(
        self,
        current_profile: DeepUserProfile,
        new_text: str,
        learning_rate: float = 0.1
    ) -> DeepUserProfile:
        """在线学习更新画像"""

        # 编码新文本
        new_embedding = self.encode_text(new_text)
        new_features = self.profile_generator(new_embedding)

        # 指数移动平均更新
        updated_embedding = (
            (1 - learning_rate) * current_profile.embedding +
            learning_rate * new_features
        )

        # 重新预测偏好
        voice_prefs = self.voice_predictor(updated_embedding)
        language_prefs = self.language_predictor(updated_embedding)
        interaction_prefs = self.interaction_predictor(updated_embedding)

        # 更新置信度
        confidence = torch.sigmoid(torch.norm(updated_embedding)).item()

        return DeepUserProfile(
            user_id=current_profile.user_id,
            embedding=updated_embedding.detach(),
            voice_preferences=voice_prefs,
            language_preferences=language_prefs,
            interaction_preferences=interaction_prefs,
            confidence=min(confidence, 1.0),
            version=current_profile.version + 1,
            created_at=current_profile.created_at,
            updated_at=datetime.now()
        )

    def save(self, path: str):
        """保存模型"""
        torch.save({
            'model_state_dict': self.state_dict(),
            'model_name': self.text_encoder.config.name_or_path if self.text_encoder else None
        }, path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Model loaded from {path}")


# 便捷函数
def create_default_profile(user_id: str) -> DeepUserProfile:
    """创建默认用户画像"""
    profiler = DeepUserProfiler()
    return profiler([], user_id)