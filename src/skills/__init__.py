"""
Skills模块 - 多角色协同系统
"""
from src.skills.role_skills import (
    RoleSkill,
    RoleType,
    VoiceConfig,
    RoleSkill,
    get_role,
    get_all_roles,
    get_role_by_trait,
    get_role_by_expertise,
    ROLE_SKILLS
)

from src.skills.multi_role_system import (
    MultiRoleSystem,
    RoleManager,
    RoleCoordinator,
    RoleTransitionEngine,
    MultiRoleResponse,
    RoleTransition,
    TransitionStyle
)

__all__ = [
    # Role Skills
    "RoleSkill",
    "RoleType",
    "VoiceConfig",
    "get_role",
    "get_all_roles",
    "get_role_by_trait",
    "get_role_by_expertise",
    "ROLE_SKILLS",

    # Multi-Role System
    "MultiRoleSystem",
    "RoleManager",
    "RoleCoordinator",
    "RoleTransitionEngine",
    "MultiRoleResponse",
    "RoleTransition",
    "TransitionStyle"
]