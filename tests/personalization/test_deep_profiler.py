"""
测试深度学习画像引擎
"""
import pytest
import torch
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.personalization.deep_profiler import (
    DeepUserProfiler,
    DeepUserProfile,
    create_default_profile
)


class TestDeepUserProfiler:
    """测试深度学习用户画像引擎"""

    def test_profiler_initialization(self):
        """测试画像引擎初始化"""
        profiler = DeepUserProfiler()

        assert profiler is not None
        assert profiler.voice_predictor is not None
        assert profiler.language_predictor is not None
        assert profiler.interaction_predictor is not None

    def test_create_default_profile(self):
        """测试创建默认画像"""
        profile = create_default_profile("test-user")

        assert profile is not None
        assert profile.user_id == "test-user"
        assert profile.embedding is not None
        assert profile.embedding.shape == torch.Size([1, 256])
        assert 0 <= profile.confidence <= 1

    def test_profile_generation(self):
        """测试画像生成"""
        profiler = DeepUserProfiler()

        # 模拟用户历史
        text_history = [
            "你好，请讲一个故事",
            "我喜欢听有趣的故事",
            "你讲得真好"
        ]

        profile = profiler(text_history, "test-user-2")

        assert profile is not None
        assert profile.user_id == "test-user-2"
        assert profile.voice_preferences is not None
        assert profile.language_preferences is not None
        assert profile.interaction_preferences is not None

    def test_voice_preferences(self):
        """测试声音偏好预测"""
        profiler = DeepUserProfiler()
        profile = profiler(["测试文本"], "test-user-3")

        voice_prefs = profile.voice_preferences

        # 检查声音偏好范围
        assert 0.5 <= voice_prefs.speed <= 2.0
        assert -50 <= voice_prefs.pitch <= 50
        assert voice_prefs.timbre_weights.shape == torch.Size([1, 10])
        assert voice_prefs.emotion_intensities.shape == torch.Size([1, 8])

        # 检查概率分布
        assert torch.allclose(voice_prefs.timbre_weights.sum(dim=-1), torch.tensor([1.0]), atol=1e-5)
        assert torch.allclose(voice_prefs.emotion_intensities.sum(dim=-1), torch.tensor([1.0]), atol=1e-5)

    def test_language_preferences(self):
        """测试语言风格偏好预测"""
        profiler = DeepUserProfiler()
        profile = profiler(["测试文本"], "test-user-4")

        lang_prefs = profile.language_preferences

        # 检查语言偏好范围
        assert 0 <= lang_prefs.formality <= 1
        assert 0 <= lang_prefs.humor <= 1
        assert 0 <= lang_prefs.detail <= 1
        assert 0 <= lang_prefs.emotion_expression <= 1

    def test_interaction_preferences(self):
        """测试交互模式偏好预测"""
        profiler = DeepUserProfiler()
        profile = profiler(["测试文本"], "test-user-5")

        inter_prefs = profile.interaction_preferences

        # 检查交互偏好
        assert 0 <= inter_prefs.response_length <= 1
        assert inter_prefs.preferred_role in ["storyteller", "mentor", "companion", "expert", "friend"]
        assert 0 <= inter_prefs.emotional_sensitivity <= 1

    def test_profile_update(self):
        """测试画像在线更新"""
        profiler = DeepUserProfiler()

        # 初始画像
        initial_profile = profiler(["初始文本"], "test-user-6")

        # 更新画像
        updated_profile = profiler.update_profile(
            initial_profile,
            "新的交互文本",
            learning_rate=0.2
        )

        assert updated_profile is not None
        assert updated_profile.version == initial_profile.version + 1
        assert updated_profile.user_id == initial_profile.user_id

    def test_empty_history(self):
        """测试空历史情况"""
        profiler = DeepUserProfiler()
        profile = profiler([], "test-user-7")

        assert profile is not None
        assert profile.embedding is not None

    def test_long_history(self):
        """测试长历史情况（超过10条）"""
        profiler = DeepUserProfiler()

        # 创建超过10条的历史
        long_history = [f"文本 {i}" for i in range(15)]

        profile = profiler(long_history, "test-user-8")

        assert profile is not None
        # 应该只使用最近10条


if __name__ == "__main__":
    pytest.main([__file__, "-v"])