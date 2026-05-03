"""
本地缓存降级
"""
from typing import Dict, Optional
from collections import OrderedDict
import logging

from src.models.state_models import SessionState

logger = logging.getLogger(__name__)


class LocalCache:
    """本地 LRU 缓存（Redis 不可用时的降级方案）"""

    def __init__(self, max_size: int = 100):
        """
        初始化本地缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, SessionState] = OrderedDict()
        logger.info(f"Local cache initialized with max_size={max_size}")

    async def get(self, session_id: str) -> Optional[SessionState]:
        """
        获取会话状态

        Args:
            session_id: 会话ID

        Returns:
            会话状态，如果不存在则返回 None
        """
        if session_id in self.cache:
            # LRU: 移到最后表示最近使用
            self.cache.move_to_end(session_id)
            return self.cache[session_id]
        return None

    async def set(self, session_id: str, state: SessionState):
        """
        设置会话状态

        Args:
            session_id: 会话ID
            state: 会话状态
        """
        if session_id in self.cache:
            # 更新已存在的条目
            self.cache.move_to_end(session_id)
        else:
            # 添加新条目
            if len(self.cache) >= self.max_size:
                # LRU: 删除最旧的条目
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Evicted session {oldest_key} from cache")

        self.cache[session_id] = state

    async def delete(self, session_id: str):
        """
        删除会话状态

        Args:
            session_id: 会话ID
        """
        if session_id in self.cache:
            del self.cache[session_id]
            logger.debug(f"Deleted session {session_id} from cache")

    async def exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话ID

        Returns:
            是否存在
        """
        return session_id in self.cache

    async def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("Local cache cleared")

    def get_size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)

    def get_stats(self) -> dict:
        """获取缓存统计"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "usage_percent": len(self.cache) / self.max_size * 100
        }
