"""
会话管理器
"""
from typing import Optional
import logging

from src.models.state_models import SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器"""

    def __init__(self, state_manager=None):
        if state_manager is None:
            from src.state.redis_manager import RedisStateManager
            state_manager = RedisStateManager(use_redis=False)
        self.state_manager = state_manager
        logger.info("Session manager initialized")

    async def initialize(self):
        """初始化会话管理器"""
        await self.state_manager.connect()
        logger.info("Session manager connected to state backend")

    async def shutdown(self):
        """关闭会话管理器"""
        await self.state_manager.disconnect()
        logger.info("Session manager disconnected")

    async def create_session(self, session_id: str) -> SessionState:
        """
        创建新会话

        Args:
            session_id: 会话ID

        Returns:
            新创建的会话状态
        """
        state = SessionState(session_id=session_id)
        await self.state_manager.set(session_id, state)
        logger.info(f"Created session: {session_id}")
        return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            会话状态，如果不存在则返回 None
        """
        return await self.state_manager.get(session_id)

    async def update_session(self, session_id: str, state: SessionState):
        """
        更新会话

        Args:
            session_id: 会话ID
            state: 会话状态
        """
        state.update_activity()
        await self.state_manager.set(session_id, state)
        logger.debug(f"Updated session: {session_id}")

    async def delete_session(self, session_id: str):
        """
        删除会话

        Args:
            session_id: 会话ID
        """
        await self.state_manager.delete(session_id)
        logger.info(f"Deleted session: {session_id}")

    async def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话ID

        Returns:
            是否存在
        """
        return await self.state_manager.exists(session_id)

    async def get_or_create_session(self, session_id: str) -> SessionState:
        """
        获取或创建会话

        Args:
            session_id: 会话ID

        Returns:
            会话状态
        """
        state = await self.get_session(session_id)

        if state is None:
            state = await self.create_session(session_id)
        else:
            # 恢复会话，更新活动时间
            state.update_activity()
            await self.update_session(session_id, state)
            logger.info(f"Resumed session: {session_id}")

        return state

    async def add_interaction(
        self,
        session_id: str,
        user_input: str,
        assistant_response: str
    ):
        """
        添加对话记录

        Args:
            session_id: 会话ID
            user_input: 用户输入
            assistant_response: 助手回复
        """
        state = await self.get_session(session_id)

        if state:
            state.add_interaction(user_input, assistant_response)
            await self.update_session(session_id, state)

    async def get_stats(self) -> dict:
        """获取统计信息"""
        return await self.state_manager.get_stats()
