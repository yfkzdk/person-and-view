"""
Redis 状态管理器
"""
from typing import Optional, Dict, Any
import json
import logging

from src.models.state_models import SessionState
from src.state.local_cache import LocalCache

logger = logging.getLogger(__name__)


class RedisStateManager:
    """Redis 状态管理器"""

    def __init__(self, use_redis: bool = False, redis_url: str = "redis://localhost:6379"):
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.redis_client = None
        self.local_cache = LocalCache()

        if use_redis:
            self._init_redis()

    def _init_redis(self):
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url)
            logger.info(f"Redis connected: {self.redis_url}")
        except ImportError:
            logger.warning("redis package not installed, falling back to local cache")
            self.use_redis = False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, falling back to local cache")
            self.use_redis = False

    async def connect(self):
        """连接（兼容 SessionManager）"""
        if self.use_redis and not self.redis_client:
            self._init_redis()

    async def disconnect(self):
        """断开连接"""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.warning(f"Redis stats error, falling back to local cache: {e}")

    async def get(self, session_id: str) -> Optional[SessionState]:
        if self.use_redis and self.redis_client:
            try:
                data = await self.redis_client.get(f"session:{session_id}")
                if data:
                    return SessionState(**json.loads(data))
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        return await self.local_cache.get(session_id)

    async def set(self, session_id: str, state: SessionState):
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.set(
                    f"session:{session_id}",
                    state.model_dump_json(),
                    ex=3600
                )
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        await self.local_cache.set(session_id, state)

    async def delete(self, session_id: str):
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        await self.local_cache.delete(session_id)

    async def exists(self, session_id: str) -> bool:
        if self.use_redis and self.redis_client:
            try:
                return await self.redis_client.exists(f"session:{session_id}") > 0
            except Exception as e:
                logger.error(f"Redis exists error: {e}")
        return await self.local_cache.exists(session_id)

    async def get_stats(self) -> dict:
        if self.use_redis and self.redis_client:
            try:
                info = await self.redis_client.info()
                return {"backend": "redis", "keys": info.get("db0", {}).get("keys", 0)}
            except Exception as e:
                logger.warning(f"Redis stats error, falling back to local cache: {e}")
        return {"backend": "local_cache", "size": self.local_cache.get_size()}
