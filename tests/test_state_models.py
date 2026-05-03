"""
状态模型测试
"""
import pytest
from src.models.state_models import SessionState, VectorClock, DirectorCommandState


def test_session_state_creation():
    """测试会话状态创建"""
    state = SessionState(session_id="test-001")

    assert state.session_id == "test-001"
    assert len(state.conversation_history) == 0
    assert state.current_emotion == "neutral"


def test_vector_clock_creation():
    """测试向量时钟创建"""
    clock = VectorClock(node_id="node-1")

    assert clock.node_id == "node-1"
    assert clock.get_time("node-1") == 0


def test_vector_clock_increment():
    """测试向量时钟递增"""
    clock = VectorClock(node_id="node-1")

    clock.increment()
    assert clock.get_time("node-1") == 1

    clock.increment()
    assert clock.get_time("node-1") == 2


def test_vector_clock_merge():
    """测试向量时钟合并"""
    clock1 = VectorClock(node_id="node-1")
    clock1.increment()

    clock2 = VectorClock(node_id="node-2")
    clock2.increment()
    clock2.increment()

    merged = clock1.merge(clock2)

    assert merged.get_time("node-1") == 1
    assert merged.get_time("node-2") == 2


def test_vector_clock_to_dict():
    """测试向量时钟转换为字典"""
    clock = VectorClock(node_id="node-1")
    clock.increment()

    data = clock.to_dict()

    assert data["node-1"] == 1


def test_vector_clock_from_dict():
    """测试从字典创建向量时钟"""
    data = {"node-1": 5, "node-2": 3}
    clock = VectorClock.from_dict(data, node_id="node-1")

    assert clock.get_time("node-1") == 5
    assert clock.get_time("node-2") == 3


def test_session_state_add_interaction():
    """测试添加对话记录"""
    state = SessionState(session_id="test-001")

    state.add_interaction("你好", "你好！")

    assert len(state.conversation_history) == 1
    assert state.total_interactions == 1
    assert state.conversation_history[0]["user"] == "你好"


def test_session_state_increment_clock():
    """测试会话状态向量时钟递增"""
    state = SessionState(session_id="test-001")

    state.increment_clock()
    assert state.vector_clock["edge"] == 1

    state.increment_clock("cloud")
    assert state.vector_clock["cloud"] == 1


def test_director_command_state():
    """测试导演指令状态"""
    cmd_state = DirectorCommandState(
        command="speed_up",
        value=1.5
    )

    assert cmd_state.command == "speed_up"
    assert cmd_state.value == 1.5
    assert cmd_state.applied is False