"""
会话管理器测试
"""
import pytest
from src.state.session_manager import SessionManager
from src.state.redis_manager import RedisStateManager
from src.models.state_models import SessionState


@pytest.mark.asyncio
async def test_session_manager_creation():
    """测试会话管理器创建"""
    manager = SessionManager()
    assert manager.state_manager is not None


@pytest.mark.asyncio
async def test_create_session():
    """测试创建会话"""
    manager = SessionManager()
    await manager.initialize()

    state = await manager.create_session("test-001")

    assert state.session_id == "test-001"
    assert len(state.conversation_history) == 0


@pytest.mark.asyncio
async def test_get_session():
    """测试获取会话"""
    manager = SessionManager()
    await manager.initialize()

    await manager.create_session("test-001")
    state = await manager.get_session("test-001")

    assert state is not None
    assert state.session_id == "test-001"


@pytest.mark.asyncio
async def test_update_session():
    """测试更新会话"""
    manager = SessionManager()
    await manager.initialize()

    state = await manager.create_session("test-001")
    state.current_emotion = "happy"

    await manager.update_session("test-001", state)

    retrieved = await manager.get_session("test-001")
    assert retrieved.current_emotion == "happy"


@pytest.mark.asyncio
async def test_delete_session():
    """测试删除会话"""
    manager = SessionManager()
    await manager.initialize()

    await manager.create_session("test-001")
    await manager.delete_session("test-001")

    state = await manager.get_session("test-001")
    assert state is None


@pytest.mark.asyncio
async def test_session_exists():
    """测试会话存在检查"""
    manager = SessionManager()
    await manager.initialize()

    exists_before = await manager.session_exists("test-001")
    assert exists_before is False

    await manager.create_session("test-001")

    exists_after = await manager.session_exists("test-001")
    assert exists_after is True


@pytest.mark.asyncio
async def test_get_or_create_session():
    """测试获取或创建会话"""
    manager = SessionManager()
    await manager.initialize()

    # 第一次应该创建
    state1 = await manager.get_or_create_session("test-001")
    assert state1.session_id == "test-001"

    # 第二次应该获取已存在的
    state2 = await manager.get_or_create_session("test-001")
    assert state2.session_id == "test-001"


@pytest.mark.asyncio
async def test_add_interaction():
    """测试添加对话记录"""
    manager = SessionManager()
    await manager.initialize()

    await manager.create_session("test-001")
    await manager.add_interaction("test-001", "你好", "你好！")

    state = await manager.get_session("test-001")
    assert len(state.conversation_history) == 1
    assert state.total_interactions == 1


@pytest.mark.asyncio
async def test_get_stats():
    """测试获取统计"""
    manager = SessionManager()
    await manager.initialize()

    stats = await manager.get_stats()

    assert "redis_available" in stats
    assert "local_cache" in stats
