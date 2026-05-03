"""
用户画像管理器 - 管理和持久化用户画像
"""
import json
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
import torch

from src.personalization.deep_profiler import (
    DeepUserProfiler,
    DeepUserProfile
)

logger = logging.getLogger(__name__)


class UserProfileManager:
    """用户画像管理器"""

    def __init__(
        self,
        profiler: DeepUserProfiler,
        storage_path: str = "data/profiles"
    ):
        """
        初始化用户画像管理器

        Args:
            profiler: 深度学习画像引擎
            storage_path: 画像存储路径
        """
        self.profiler = profiler
        self.storage_path = storage_path
        self.profiles: Dict[str, DeepUserProfile] = {}

        # 创建存储目录
        os.makedirs(storage_path, exist_ok=True)
        logger.info(f"UserProfileManager initialized with storage: {storage_path}")

    async def get_profile(self, user_id: str) -> DeepUserProfile:
        """
        获取用户画像

        Args:
            user_id: 用户ID

        Returns:
            用户画像
        """
        # 1. 检查内存缓存
        if user_id in self.profiles:
            logger.debug(f"Profile found in memory: {user_id}")
            return self.profiles[user_id]

        # 2. 尝试从磁盘加载
        profile = self._load_profile(user_id)

        if profile is not None:
            logger.info(f"Profile loaded from disk: {user_id}")
            self.profiles[user_id] = profile
            return profile

        # 3. 创建新画像
        logger.info(f"Creating new profile: {user_id}")
        new_profile = self.profiler([], user_id)
        self.profiles[user_id] = new_profile
        await self.save_profile(user_id)

        return new_profile

    async def update_profile(
        self,
        user_id: str,
        new_interaction: str,
        learning_rate: float = 0.1
    ) -> DeepUserProfile:
        """
        更新用户画像

        Args:
            user_id: 用户ID
            new_interaction: 新的交互文本
            learning_rate: 学习率

        Returns:
            更新后的画像
        """
        # 获取当前画像
        current_profile = await self.get_profile(user_id)

        # 在线学习更新
        updated_profile = self.profiler.update_profile(
            current_profile,
            new_interaction,
            learning_rate
        )

        # 更新缓存
        self.profiles[user_id] = updated_profile

        # 保存到磁盘
        await self.save_profile(user_id)

        logger.info(f"Profile updated: {user_id} (version {updated_profile.version})")

        return updated_profile

    async def save_profile(self, user_id: str):
        """
        保存用户画像到磁盘

        Args:
            user_id: 用户ID
        """
        if user_id not in self.profiles:
            logger.warning(f"Profile not found: {user_id}")
            return

        profile = self.profiles[user_id]

        # 序列化画像
        profile_dict = {
            "user_id": profile.user_id,
            "embedding": profile.embedding.cpu().numpy().tolist(),
            "voice_preferences": {
                "timbre_weights": profile.voice_preferences.timbre_weights.cpu().numpy().tolist(),
                "speed": profile.voice_preferences.speed,
                "pitch": profile.voice_preferences.pitch,
                "emotion_intensities": profile.voice_preferences.emotion_intensities.cpu().numpy().tolist()
            },
            "language_preferences": {
                "formality": profile.language_preferences.formality,
                "humor": profile.language_preferences.humor,
                "detail": profile.language_preferences.detail,
                "emotion_expression": profile.language_preferences.emotion_expression
            },
            "interaction_preferences": {
                "response_length": profile.interaction_preferences.response_length,
                "preferred_role": profile.interaction_preferences.preferred_role,
                "emotional_sensitivity": profile.interaction_preferences.emotional_sensitivity
            },
            "confidence": profile.confidence,
            "version": profile.version,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
        }

        # 保存到文件
        file_path = os.path.join(self.storage_path, f"{user_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile_dict, f, indent=2, ensure_ascii=False)

        logger.debug(f"Profile saved: {file_path}")

    def _load_profile(self, user_id: str) -> Optional[DeepUserProfile]:
        """
        从磁盘加载用户画像

        Args:
            user_id: 用户ID

        Returns:
            用户画像或None
        """
        file_path = os.path.join(self.storage_path, f"{user_id}.json")

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                profile_dict = json.load(f)

            # 反序列化画像
            from src.personalization.deep_profiler import (
                VoicePreferences,
                LanguagePreferences,
                InteractionPreferences
            )

            profile = DeepUserProfile(
                user_id=profile_dict["user_id"],
                embedding=torch.tensor(profile_dict["embedding"]),
                voice_preferences=VoicePreferences(
                    timbre_weights=torch.tensor(profile_dict["voice_preferences"]["timbre_weights"]),
                    speed=profile_dict["voice_preferences"]["speed"],
                    pitch=profile_dict["voice_preferences"]["pitch"],
                    emotion_intensities=torch.tensor(profile_dict["voice_preferences"]["emotion_intensities"])
                ),
                language_preferences=LanguagePreferences(
                    formality=profile_dict["language_preferences"]["formality"],
                    humor=profile_dict["language_preferences"]["humor"],
                    detail=profile_dict["language_preferences"]["detail"],
                    emotion_expression=profile_dict["language_preferences"]["emotion_expression"]
                ),
                interaction_preferences=InteractionPreferences(
                    response_length=profile_dict["interaction_preferences"]["response_length"],
                    preferred_role=profile_dict["interaction_preferences"]["preferred_role"],
                    emotional_sensitivity=profile_dict["interaction_preferences"]["emotional_sensitivity"]
                ),
                confidence=profile_dict["confidence"],
                version=profile_dict["version"],
                created_at=datetime.fromisoformat(profile_dict["created_at"]) if profile_dict.get("created_at") else None,
                updated_at=datetime.fromisoformat(profile_dict["updated_at"]) if profile_dict.get("updated_at") else None
            )

            return profile

        except Exception as e:
            logger.error(f"Failed to load profile {user_id}: {e}")
            return None

    def get_all_profiles(self) -> List[str]:
        """获取所有用户ID列表"""
        if not os.path.exists(self.storage_path):
            return []

        return [
            f.replace('.json', '')
            for f in os.listdir(self.storage_path)
            if f.endswith('.json')
        ]

    async def delete_profile(self, user_id: str):
        """删除用户画像"""
        # 从内存中删除
        if user_id in self.profiles:
            del self.profiles[user_id]

        # 从磁盘删除
        file_path = os.path.join(self.storage_path, f"{user_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Profile deleted: {user_id}")