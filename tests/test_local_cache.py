"""
本地缓存测试
"""
import pytest
from src.state.local_cache import LocalCache
from src.models.state_models import SessionState


@pytest.mark.asyncio
async def test_local_cache_creation():
    """测试本地缓存创建"""
    cache = LocalCache(max_size=10)

    assert cache.max_size == 10
    assert cache.get_size() == 0


@pytest.mark.asyncio
async def test_local_cache_set_get():
    """测试设置和获取"""
    cache = LocalCache(max_size=10)
    state = SessionState(session_id="test-001")

    await cache.set("test-001", state)

    retrieved = await cache.get("test-001")
    assert retrieved is not None
    assert retrieved.session_id == "test-001"


@pytest.mark.asyncio
async def test_local_cache_delete():
    """测试删除"""
    cache = LocalCache(max_size=10)
    state = SessionState(session_id="test-001")

    await cache.set("test-001", state)
    await cache.delete("test-001")

    retrieved = await cache.get("test-001")
    assert retrieved is None


@pytest.mark.asyncio
async def test_local_cache_exists():
    """测试存在检查"""
    cache = LocalCache(max_size=10)
    state = SessionState(session_id="test-001")

    exists_before = await cache.exists("test-001")
    assert exists_before is False

    await cache.set("test-001", state)

    exists_after = await cache.exists("test-001")
    assert exists_after is True


@pytest.mark.asyncio
async def test_local_cache_lru_eviction():
    """测试 LRU 淘汰"""
    cache = LocalCache(max_size=3)

    # 添加 3 个条目
    for i in range(3):
        state = SessionState(session_id=f"test-{i}")
        await cache.set(f"test-{i}", state)

    assert cache.get_size() == 3

    # 添加第 4 个条目，应该淘汰最旧的
    state = SessionState(session_id="test-3")
    await cache.set("test-3", state)

    assert cache.get_size() == 3

    # test-0 应该被淘汰
    retrieved = await cache.get("test-0")
    assert retrieved is None

    # test-3 应该存在
    retrieved = await cache.get("test-3")
    assert retrieved is not None


@pytest.mark.asyncio
async def test_local_cache_clear():
    """测试清空缓存"""
    cache = LocalCache(max_size=10)

    for i in range(5):
        state = SessionState(session_id=f"test-{i}")
        await cache.set(f"test-{i}", state)

    assert cache.get_size() == 5

    await cache.clear()

    assert cache.get_size() == 0


@pytest.mark.asyncio
async def test_local_cache_stats():
    """测试缓存统计"""
    cache = LocalCache(max_size=10)

    for i in range(5):
        state = SessionState(session_id=f"test-{i}")
        await cache.set(f"test-{i}", state)

    stats = cache.get_stats()

    assert stats["size"] == 5
    assert stats["max_size"] == 10
    assert stats["usage_percent"] == 50.0
