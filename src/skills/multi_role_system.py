"""
多角色协同系统 - 企业级实现
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.skills.role_skills import (
    RoleSkill,
    get_role,
    get_all_roles,
    ROLE_SKILLS
)
from src.personalization.deep_profiler import DeepUserProfile

logger = logging.getLogger(__name__)


class TransitionStyle(Enum):
    """角色转换风格"""
    HANDOFF = "handoff"          # 直接交接
    COLLABORATION = "collaboration"  # 协作过渡
    EVOLUTION = "evolution"      # 自然演变


@dataclass
class RoleTransition:
    """角色转换"""
    from_role: RoleSkill
    to_role: RoleSkill
    style: TransitionStyle
    reason: str
    transition_text: str


@dataclass
class MultiRoleResponse:
    """多角色响应"""
    content: str
    audio: Optional[bytes] = None
    roles: List[RoleSkill] = None
    coordination_metadata: Dict = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.coordination_metadata is None:
            self.coordination_metadata = {}


class RoleManager:
    """角色管理器"""

    def __init__(self):
        self.available_roles = ROLE_SKILLS
        logger.info(f"RoleManager initialized with {len(self.available_roles)} roles")

    async def select_primary_role(
        self,
        user_input: str,
        user_profile: DeepUserProfile,
        context: Optional[Dict] = None
    ) -> RoleSkill:
        """选择主角色"""

        # 1. 检查用户明确指定
        explicit_role = self._detect_explicit_role(user_input)
        if explicit_role:
            logger.info(f"Explicit role selected: {explicit_role.id}")
            return explicit_role

        # 2. 基于用户画像偏好
        preferred_role_id = user_profile.interaction_preferences.preferred_role
        if preferred_role_id in self.available_roles:
            role = self.available_roles[preferred_role_id]
            logger.info(f"Profile-based role selected: {role.id}")
            return role

        # 3. 基于输入内容分析
        content_based_role = self._analyze_content(user_input)
        if content_based_role:
            logger.info(f"Content-based role selected: {content_based_role.id}")
            return content_based_role

        # 4. 默认角色
        default_role = self.available_roles["companion"]
        logger.info(f"Default role selected: {default_role.id}")
        return default_role

    async def select_supporting_roles(
        self,
        user_input: str,
        primary_role: RoleSkill,
        context: Optional[Dict] = None
    ) -> List[RoleSkill]:
        """选择辅助角色"""

        supporting = []

        # 检查是否需要专业知识
        if self._needs_expertise(user_input) and primary_role.id != "expert":
            supporting.append(self.available_roles["expert"])

        # 检查是否需要情感支持
        if self._needs_emotional_support(user_input) and primary_role.id not in ["companion", "friend"]:
            supporting.append(self.available_roles["companion"])

        # 检查是否需要教学引导
        if self._needs_teaching(user_input) and primary_role.id != "mentor":
            supporting.append(self.available_roles["mentor"])

        if supporting:
            logger.info(f"Supporting roles: {[r.id for r in supporting]}")

        return supporting

    def _detect_explicit_role(self, text: str) -> Optional[RoleSkill]:
        """检测明确指定的角色"""
        text_lower = text.lower()

        role_keywords = {
            "storyteller": ["讲故事", "故事", "叙述"],
            "mentor": ["教我", "怎么", "如何", "学习"],
            "companion": ["聊天", "聊聊", "谈心"],
            "expert": ["专业", "专家", "分析"],
            "friend": ["朋友", "倾诉", "分享"]
        }

        for role_id, keywords in role_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return self.available_roles.get(role_id)

        return None

    def _analyze_content(self, text: str) -> Optional[RoleSkill]:
        """分析内容选择角色"""
        # 简单的关键词匹配
        # 实际项目中可以使用更复杂的NLP分析

        if any(kw in text for kw in ["故事", "从前", "很久以前"]):
            return self.available_roles["storyteller"]

        if any(kw in text for kw in ["为什么", "怎么", "如何"]):
            return self.available_roles["mentor"]

        if any(kw in text for kw in ["难过", "开心", "心情"]):
            return self.available_roles["companion"]

        return None

    def _needs_expertise(self, text: str) -> bool:
        """判断是否需要专业知识"""
        expertise_keywords = ["专业", "数据", "分析", "研究", "科学"]
        return any(kw in text for kw in expertise_keywords)

    def _needs_emotional_support(self, text: str) -> bool:
        """判断是否需要情感支持"""
        emotion_keywords = ["难过", "伤心", "压力", "焦虑", "担心"]
        return any(kw in text for kw in emotion_keywords)

    def _needs_teaching(self, text: str) -> bool:
        """判断是否需要教学引导"""
        teaching_keywords = ["学习", "理解", "明白", "教我"]
        return any(kw in text for kw in teaching_keywords)


class RoleCoordinator:
    """角色协调器"""

    async def coordinate(
        self,
        primary_role: RoleSkill,
        supporting_roles: List[RoleSkill],
        user_input: str,
        user_profile: DeepUserProfile
    ) -> MultiRoleResponse:
        """协调多个角色生成响应"""

        # 1. 主角色生成主体内容
        primary_response = await self._generate_role_response(
            primary_role,
            user_input,
            user_profile
        )

        # 2. 辅助角色补充
        supporting_responses = []
        for role in supporting_roles:
            supplement = await self._generate_supplement(
                role,
                primary_response,
                user_input,
                user_profile
            )
            supporting_responses.append(supplement)

        # 3. 融合响应
        fused_content = self._fuse_responses(
            primary_response,
            supporting_responses
        )

        return MultiRoleResponse(
            content=fused_content,
            roles=[primary_role] + supporting_roles,
            coordination_metadata={
                "primary_contribution": 0.7,
                "supporting_contributions": [0.3 / len(supporting_roles)] * len(supporting_roles) if supporting_roles else []
            }
        )

    async def _generate_role_response(
        self,
        role: RoleSkill,
        user_input: str,
        user_profile: DeepUserProfile
    ) -> str:
        """生成角色响应"""
        # 这里应该调用LLM生成响应
        # 简化版本：返回模板响应
        return f"[{role.name}] 关于'{user_input}'的响应..."

    async def _generate_supplement(
        self,
        role: RoleSkill,
        primary_response: str,
        user_input: str,
        user_profile: DeepUserProfile
    ) -> str:
        """生成补充内容"""
        return f"[{role.name}] 补充观点..."

    def _fuse_responses(
        self,
        primary: str,
        supporting: List[str]
    ) -> str:
        """融合多个响应"""
        if not supporting:
            return primary

        fused = primary + "\n\n"
        fused += "\n\n".join(supporting)
        return fused


class RoleTransitionEngine:
    """角色转换引擎"""

    async def plan_transition(
        self,
        current_role: RoleSkill,
        context: Dict
    ) -> Optional[RoleTransition]:
        """规划角色转换"""

        # 分析转换需求
        transition_reason = self._analyze_transition_need(context)

        if not transition_reason:
            return None

        # 选择目标角色
        target_role = await self._select_target_role(
            transition_reason,
            context
        )

        if not target_role or target_role.id == current_role.id:
            return None

        # 设计转换方式
        transition_style = self._design_transition_style(
            current_role,
            target_role,
            transition_reason
        )

        # 生成转换文本
        transition_text = self._generate_transition_text(transition_style)

        return RoleTransition(
            from_role=current_role,
            to_role=target_role,
            style=transition_style,
            reason=transition_reason,
            transition_text=transition_text
        )

    def _analyze_transition_need(self, context: Dict) -> Optional[str]:
        """分析转换需求"""
        # 基于上下文判断是否需要转换
        # 简化版本
        return None

    async def _select_target_role(
        self,
        reason: str,
        context: Dict
    ) -> Optional[RoleSkill]:
        """选择目标角色"""
        return None

    def _design_transition_style(
        self,
        from_role: RoleSkill,
        to_role: RoleSkill,
        reason: str
    ) -> TransitionStyle:
        """设计转换风格"""
        return TransitionStyle.EVOLUTION

    def _generate_transition_text(self, style: TransitionStyle) -> str:
        """生成转换文本"""
        texts = {
            TransitionStyle.HANDOFF: "让我换个角度来回答你...",
            TransitionStyle.COLLABORATION: "我想请我的朋友来补充一下...",
            TransitionStyle.EVOLUTION: "现在让我用另一种方式来说..."
        }
        return texts.get(style, "")


class MultiRoleSystem:
    """多角色协同系统"""

    def __init__(self):
        self.role_manager = RoleManager()
        self.role_coordinator = RoleCoordinator()
        self.transition_engine = RoleTransitionEngine()

        logger.info("MultiRoleSystem initialized")

    async def process_with_roles(
        self,
        user_input: str,
        user_profile: DeepUserProfile,
        context: Optional[Dict] = None
    ) -> MultiRoleResponse:
        """使用多角色处理用户输入"""

        # 1. 确定主角色
        primary_role = await self.role_manager.select_primary_role(
            user_input,
            user_profile,
            context
        )

        # 2. 确定辅助角色
        supporting_roles = await self.role_manager.select_supporting_roles(
            user_input,
            primary_role,
            context
        )

        # 3. 角色协同生成
        if supporting_roles:
            response = await self.role_coordinator.coordinate(
                primary_role,
                supporting_roles,
                user_input,
                user_profile
            )
        else:
            # 单角色生成
            content = await self.role_coordinator._generate_role_response(
                primary_role,
                user_input,
                user_profile
            )
            response = MultiRoleResponse(
                content=content,
                roles=[primary_role]
            )

        # 4. 检查是否需要角色转换
        if context:
            transition = await self.transition_engine.plan_transition(
                primary_role,
                context
            )
            if transition:
                logger.info(f"Role transition planned: {transition.from_role.id} -> {transition.to_role.id}")

        return response