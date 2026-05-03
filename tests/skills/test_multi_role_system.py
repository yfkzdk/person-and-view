"""
测试多角色协同系统
"""
import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.skills.role_skills import (
    RoleSkill,
    get_role,
    get_all_roles,
    get_role_by_trait,
    get_role_by_expertise
)
from src.skills.multi_role_system import (
    MultiRoleSystem,
    RoleManager,
    RoleCoordinator,
    RoleTransitionEngine,
    TransitionStyle
)
from src.personalization.deep_profiler import (
    DeepUserProfile,
    VoicePreferences,
    LanguagePreferences,
    InteractionPreferences
)
import torch


class TestRoleSkills:
    """测试角色定义"""

    def test_get_role(self):
        """测试获取角色"""
        role = get_role("storyteller")

        assert role is not None
        assert role.id == "storyteller"
        assert role.name == "故事讲述者"
        assert len(role.traits) > 0

    def test_get_all_roles(self):
        """测试获取所有角色"""
        roles = get_all_roles()

        assert len(roles) == 5
        assert "storyteller" in roles
        assert "mentor" in roles
        assert "companion" in roles

    def test_get_role_by_trait(self):
        """测试根据特质查找角色"""
        roles = get_role_by_trait("温暖")

        assert len(roles) > 0
        assert any(r.id == "storyteller" for r in roles)

    def test_get_role_by_expertise(self):
        """测试根据专长查找角色"""
        roles = get_role_by_expertise("故事创作")

        assert len(roles) > 0
        assert any(r.id == "storyteller" for r in roles)

    def test_role_voice_config(self):
        """测试角色声音配置"""
        role = get_role("mentor")

        assert role.voice_config is not None
        assert role.voice_config.base_voice == "YunxiNeural"
        assert 0.5 <= role.voice_config.rate <= 2.0

    def test_role_emotion_mapping(self):
        """测试角色情绪映射"""
        role = get_role("companion")

        assert role.emotion_mapping is not None
        assert "joy" in role.emotion_mapping
        assert "sadness" in role.emotion_mapping


class TestRoleManager:
    """测试角色管理器"""

    @pytest.fixture
    def role_manager(self):
        return RoleManager()

    @pytest.fixture
    def mock_profile(self):
        return DeepUserProfile(
            user_id="test-user",
            embedding=torch.randn(1, 256),
            voice_preferences=VoicePreferences(
                timbre_weights=torch.randn(1, 10),
                speed=1.0,
                pitch=0.0,
                emotion_intensities=torch.randn(1, 8)
            ),
            language_preferences=LanguagePreferences(
                formality=0.5,
                humor=0.5,
                detail=0.5,
                emotion_expression=0.5
            ),
            interaction_preferences=InteractionPreferences(
                response_length=0.5,
                preferred_role="companion",
                emotional_sensitivity=0.5
            ),
            confidence=0.8
        )

    @pytest.mark.asyncio
    async def test_select_primary_role_explicit(self, role_manager, mock_profile):
        """测试明确指定的角色选择"""
        role = await role_manager.select_primary_role(
            "请讲一个故事",
            mock_profile
        )

        assert role is not None
        assert role.id == "storyteller"

    @pytest.mark.asyncio
    async def test_select_primary_role_profile_based(self, role_manager, mock_profile):
        """测试基于画像的角色选择"""
        role = await role_manager.select_primary_role(
            "你好",
            mock_profile
        )

        assert role is not None
        assert role.id == mock_profile.interaction_preferences.preferred_role

    @pytest.mark.asyncio
    async def test_select_supporting_roles(self, role_manager, mock_profile):
        """测试辅助角色选择"""
        primary_role = get_role("storyteller")

        supporting = await role_manager.select_supporting_roles(
            "我需要专业的数据分析",
            primary_role
        )

        assert len(supporting) > 0
        assert any(r.id == "expert" for r in supporting)


class TestRoleCoordinator:
    """测试角色协调器"""

    @pytest.fixture
    def coordinator(self):
        return RoleCoordinator()

    @pytest.fixture
    def mock_profile(self):
        return DeepUserProfile(
            user_id="test-user",
            embedding=torch.randn(1, 256),
            voice_preferences=VoicePreferences(
                timbre_weights=torch.randn(1, 10),
                speed=1.0,
                pitch=0.0,
                emotion_intensities=torch.randn(1, 8)
            ),
            language_preferences=LanguagePreferences(
                formality=0.5,
                humor=0.5,
                detail=0.5,
                emotion_expression=0.5
            ),
            interaction_preferences=InteractionPreferences(
                response_length=0.5,
                preferred_role="companion",
                emotional_sensitivity=0.5
            ),
            confidence=0.8
        )

    @pytest.mark.asyncio
    async def test_coordinate_single_role(self, coordinator, mock_profile):
        """测试单角色协调"""
        primary_role = get_role("companion")

        response = await coordinator.coordinate(
            primary_role,
            [],
            "你好",
            mock_profile
        )

        assert response is not None
        assert response.content is not None
        assert len(response.roles) == 1

    @pytest.mark.asyncio
    async def test_coordinate_multi_role(self, coordinator, mock_profile):
        """测试多角色协调"""
        primary_role = get_role("storyteller")
        supporting_roles = [get_role("expert")]

        response = await coordinator.coordinate(
            primary_role,
            supporting_roles,
            "讲一个关于科学的故事",
            mock_profile
        )

        assert response is not None
        assert len(response.roles) == 2


class TestRoleTransitionEngine:
    """测试角色转换引擎"""

    @pytest.fixture
    def transition_engine(self):
        return RoleTransitionEngine()

    def test_transition_style_enum(self):
        """测试转换风格枚举"""
        assert TransitionStyle.HANDOFF.value == "handoff"
        assert TransitionStyle.COLLABORATION.value == "collaboration"
        assert TransitionStyle.EVOLUTION.value == "evolution"


class TestMultiRoleSystem:
    """测试多角色协同系统"""

    @pytest.fixture
    def system(self):
        return MultiRoleSystem()

    @pytest.fixture
    def mock_profile(self):
        return DeepUserProfile(
            user_id="test-user",
            embedding=torch.randn(1, 256),
            voice_preferences=VoicePreferences(
                timbre_weights=torch.randn(1, 10),
                speed=1.0,
                pitch=0.0,
                emotion_intensities=torch.randn(1, 8)
            ),
            language_preferences=LanguagePreferences(
                formality=0.5,
                humor=0.5,
                detail=0.5,
                emotion_expression=0.5
            ),
            interaction_preferences=InteractionPreferences(
                response_length=0.5,
                preferred_role="companion",
                emotional_sensitivity=0.5
            ),
            confidence=0.8
        )

    @pytest.mark.asyncio
    async def test_process_with_roles(self, system, mock_profile):
        """测试多角色处理"""
        response = await system.process_with_roles(
            "你好，请介绍一下你自己",
            mock_profile
        )

        assert response is not None
        assert response.content is not None
        assert len(response.roles) > 0

    @pytest.mark.asyncio
    async def test_process_storyteller_request(self, system, mock_profile):
        """测试故事讲述者请求"""
        response = await system.process_with_roles(
            "请讲一个有趣的故事",
            mock_profile
        )

        assert response is not None
        assert any(r.id == "storyteller" for r in response.roles)

    @pytest.mark.asyncio
    async def test_process_mentor_request(self, system, mock_profile):
        """测试导师请求"""
        response = await system.process_with_roles(
            "教我如何学习编程",
            mock_profile
        )

        assert response is not None
        # 应该包含mentor角色或相关角色


if __name__ == "__main__":
    pytest.main([__file__, "-v"])