"""
Redis 状态管理器测试
"""
import pytest
from src.state.redis_manager import RedisStateManager
from src.models.state_models import SessionState


@pytest.mark.asyncio
async def test_redis_manager_creation():
    """测试 Redis 管理器创建"""
    manager = RedisStateManager(use_redis=False)

    assert manager.use_redis is False
    assert manager.redis_client is None


@pytest.mark.asyncio
async def test_redis_manager_local_only():
    """测试仅使用本地缓存"""
    manager = RedisStateManager(use_redis=False)
    await manager.connect()

    state = SessionState(session_id="test-001")
    await manager.set("test-001", state)

    retrieved = await manager.get("test-001")
    assert retrieved is not None
    assert retrieved.session_id == "test-001"

    assert manager.is_redis_available() is False


@pytest.mark.asyncio
async def test_redis_manager_set_get():
    """测试设置和获取"""
    manager = RedisStateManager(use_redis=False)
    await manager.connect()

    state = SessionState(session_id="test-001")
    state.current_emotion = "happy"

    await manager.set("test-001", state)

    retrieved = await manager.get("test-001")
    assert retrieved is not None
    assert retrieved.session_id == "test-001"
    assert retrieved.current_emotion == "happy"


@pytest.mark.asyncio
async def test_redis_manager_delete():
    """测试删除"""
    manager = RedisStateManager(use_redis=False)
    await manager.connect()

    state = SessionState(session_id="test-001")
    await manager.set("test-001", state)

    await manager.delete("test-001")

    retrieved = await manager.get("test-001")
    assert retrieved is None


@pytest.mark.asyncio
async def test_redis_manager_exists():
    """测试存在检查"""
    manager = RedisStateManager(use_redis=False)
    await manager.connect()

    exists_before = await manager.exists("test-001")
    assert exists_before is False

    state = SessionState(session_id="test-001")
    await manager.set("test-001", state)

    exists_after = await manager.exists("test-001")
    assert exists_after is True


@pytest.mark.asyncio
async def test_redis_manager_get_stats():
    """测试获取统计"""
    manager = RedisStateManager(use_redis=False)
    await manager.connect()

    stats = await manager.get_stats()

    assert "redis_available" in stats
    assert "local_cache" in stats
    assert stats["redis_available"] is False


@pytest.mark.asyncio
async def test_redis_manager_connect_disconnect():
    """测试连接和断开"""
    manager = RedisStateManager(use_redis=False)

    await manager.connect()
    await manager.disconnect()

    # 应该没有异常
    assert True
