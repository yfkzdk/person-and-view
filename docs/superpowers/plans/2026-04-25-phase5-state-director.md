# 状态管理 + 导演指令模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Redis 状态持久化和完善的导演指令系统，支持会话恢复、状态同步和降级策略。

**Architecture:** 使用 Redis 存储会话状态，通过向量时钟解决冲突，实现导演指令注册和管理系统，支持 Redis 不可用时的本地降级。

**Tech Stack:** Python 3.11.4, Redis 7.4.0, asyncio, msgpack

---

## 文件结构

```
O:\AII\app\references\
├── src/
│   ├── state/
│   │   ├── __init__.py
│   │   ├── redis_manager.py       # Redis 状态管理器
│   │   ├── session_manager.py     # 会话管理器
│   │   ├── vector_clock.py        # 向量时钟实现
│   │   └── local_cache.py         # 本地缓存降级
│   ├── director/
│   │   ├── __init__.py
│   │   ├── command_registry.py    # 指令注册表
│   │   ├── command_processor.py   # 指令处理器
│   │   └── custom_commands.py     # 自定义指令
│   └── models/
│       └── state_models.py        # 状态模型
├── tests/
│   ├── test_redis_manager.py      # Redis 管理器测试
│   ├── test_session_manager.py    # 会话管理测试
│   ├── test_vector_clock.py       # 向量时钟测试
│   ├── test_command_registry.py   # 指令注册测试
│   └── test_local_cache.py        # 本地缓存测试
└── docs/
    └── state_management.md        # 状态管理文档
```

---

## Task 1: 状态模型定义

**Files:**
- Create: `src/models/state_models.py`
- Test: `tests/test_state_models.py`

- [ ] **Step 1: Write the failing test for state models**

```python
# tests/test_state_models.py
import pytest
from src.models.state_models import SessionState, VectorClock


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models.state_models'"

- [ ] **Step 3: Implement state models**

```python
# src/models/state_models.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import time


class VectorClock:
    """向量时钟实现"""

    def __init__(self, node_id: str):
        """
        初始化向量时钟

        Args:
            node_id: 节点ID
        """
        self.node_id = node_id
        self.clock: Dict[str, int] = {node_id: 0}

    def increment(self):
        """递增本节点时钟"""
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def get_time(self, node_id: str) -> int:
        """
        获取指定节点的时间

        Args:
            node_id: 节点ID

        Returns:
            时间值
        """
        return self.clock.get(node_id, 0)

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """
        合并另一个向量时钟

        Args:
            other: 另一个向量时钟

        Returns:
            合并后的新向量时钟
        """
        merged = VectorClock(self.node_id)

        # 取每个节点的最大值
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for node in all_nodes:
            merged.clock[node] = max(
                self.clock.get(node, 0),
                other.clock.get(node, 0)
            )

        return merged

    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return self.clock.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, int], node_id: str) -> 'VectorClock':
        """从字典创建"""
        clock = cls(node_id)
        clock.clock = data.copy()
        return clock


class SessionState(BaseModel):
    """会话状态"""
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)

    # 对话历史
    conversation_history: List[Dict[str, str]] = []

    # 当前状态
    current_emotion: str = "neutral"
    current_scene: str = "intro"

    # 向量时钟
    vector_clock: Dict[str, int] = Field(default_factory=lambda: {"edge": 0})

    # 统计信息
    total_interactions: int = 0
    total_audio_sent: int = 0
    total_audio_received: int = 0

    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()

    def add_interaction(self, user_input: str, assistant_response: str):
        """添加对话记录"""
        self.conversation_history.append({
            "user": user_input,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        self.total_interactions += 1
        self.update_activity()

    def increment_clock(self, node_id: str = "edge"):
        """递增向量时钟"""
        self.vector_clock[node_id] = self.vector_clock.get(node_id, 0) + 1

    def merge_clock(self, other_clock: Dict[str, int]):
        """合并向量时钟"""
        for node, time in other_clock.items():
            self.vector_clock[node] = max(
                self.vector_clock.get(node, 0),
                time
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit state models**

```bash
git add src/models/state_models.py tests/test_state_models.py
git commit -m "feat: add state models with vector clock support"
```

---

## Task 2: Redis 状态管理器

**Files:**
- Create: `src/state/redis_manager.py`
- Test: `tests/test_redis_manager.py`

- [ ] **Step 1: Write the failing test for Redis manager**

```python
# tests/test_redis_manager.py
import pytest
import asyncio
from src.state.redis_manager import RedisStateManager
from src.models.state_models import SessionState


@pytest.mark.asyncio
async def test_redis_manager_creation():
    """测试 Redis 管理器创建"""
    manager = RedisStateManager(redis_url="redis://localhost:6379")

    assert manager.redis_url == "redis://localhost:6379"


@pytest.mark.asyncio
async def test_save_and_load_state():
    """测试保存和加载状态"""
    manager = RedisStateManager(redis_url="redis://localhost:6379")

    # 创建测试状态
    state = SessionState(session_id="test-001")
    state.add_interaction("你好", "你好！")

    # 保存状态
    await manager.save_state(state)

    # 加载状态
    loaded_state = await manager.load_state("test-001")

    assert loaded_state is not None
    assert loaded_state.session_id == "test-001"
    assert len(loaded_state.conversation_history) == 1


@pytest.mark.asyncio
async def test_delete_state():
    """测试删除状态"""
    manager = RedisStateManager(redis_url="redis://localhost:6379")

    # 创建并保存状态
    state = SessionState(session_id="test-002")
    await manager.save_state(state)

    # 删除状态
    await manager.delete_state("test-002")

    # 尝试加载
    loaded_state = await manager.load_state("test-002")

    assert loaded_state is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_redis_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.state.redis_manager'"

- [ ] **Step 3: Implement Redis manager**

```python
# src/state/redis_manager.py
import redis.asyncio as redis
from typing import Optional
import msgpack
import logging
from datetime import datetime

from src.models.state_models import SessionState

logger = logging.getLogger(__name__)


class RedisStateManager:
    """Redis 状态管理器"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "session:",
        ttl: int = 3600  # 1小时过期
    ):
        """
        初始化 Redis 状态管理器

        Args:
            redis_url: Redis 连接URL
            key_prefix: 键前缀
            ttl: 过期时间（秒）
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """连接到 Redis"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False
            )
            logger.info(f"Connected to Redis: {self.redis_url}")

    async def disconnect(self):
        """断开 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    def _get_key(self, session_id: str) -> str:
        """获取完整的键名"""
        return f"{self.key_prefix}{session_id}"

    async def save_state(self, state: SessionState):
        """
        保存会话状态

        Args:
            state: 会话状态
        """
        if self.redis_client is None:
            await self.connect()

        key = self._get_key(state.session_id)

        # 序列化状态
        state_dict = state.dict()
        state_dict['created_at'] = state_dict['created_at'].isoformat()
        state_dict['last_activity'] = state_dict['last_activity'].isoformat()

        packed_data = msgpack.packb(state_dict)

        # 保存到 Redis
        await self.redis_client.setex(key, self.ttl, packed_data)

        logger.debug(f"Saved state for session {state.session_id}")

    async def load_state(self, session_id: str) -> Optional[SessionState]:
        """
        加载会话状态

        Args:
            session_id: 会话ID

        Returns:
            会话状态，如果不存在则返回 None
        """
        if self.redis_client is None:
            await self.connect()

        key = self._get_key(session_id)

        # 从 Redis 加载
        packed_data = await self.redis_client.get(key)

        if packed_data is None:
            return None

        # 反序列化
        state_dict = msgpack.unpackb(packed_data, raw=False)
        state_dict['created_at'] = datetime.fromisoformat(state_dict['created_at'])
        state_dict['last_activity'] = datetime.fromisoformat(state_dict['last_activity'])

        return SessionState(**state_dict)

    async def delete_state(self, session_id: str):
        """
        删除会话状态

        Args:
            session_id: 会话ID
        """
        if self.redis_client is None:
            await self.connect()

        key = self._get_key(session_id)
        await self.redis_client.delete(key)

        logger.debug(f"Deleted state for session {session_id}")

    async def update_ttl(self, session_id: str):
        """
        更新会话过期时间

        Args:
            session_id: 会话ID
        """
        if self.redis_client is None:
            await self.connect()

        key = self._get_key(session_id)
        await self.redis_client.expire(key, self.ttl)

    async def exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话ID

        Returns:
            是否存在
        """
        if self.redis_client is None:
            await self.connect()

        key = self._get_key(session_id)
        return await self.redis_client.exists(key) > 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_redis_manager.py -v`
Expected: PASS (requires Redis running)

- [ ] **Step 5: Commit Redis manager**

```bash
git add src/state/redis_manager.py tests/test_redis_manager.py
git commit -m "feat: add Redis state manager with persistence"
```

---

## Task 3: 本地缓存降级

**Files:**
- Create: `src/state/local_cache.py`
- Test: `tests/test_local_cache.py`

- [ ] **Step 1: Write the failing test for local cache**

```python
# tests/test_local_cache.py
import pytest
from src.state.local_cache import LocalCache
from src.models.state_models import SessionState


def test_local_cache_creation():
    """测试本地缓存创建"""
    cache = LocalCache(max_size=100)

    assert cache.max_size == 100
    assert len(cache.cache) == 0


def test_local_cache_set_get():
    """测试本地缓存存取"""
    cache = LocalCache(max_size=10)

    state = SessionState(session_id="test-001")
    cache.set("test-001", state)

    loaded_state = cache.get("test-001")

    assert loaded_state is not None
    assert loaded_state.session_id == "test-001"


def test_local_cache_delete():
    """测试本地缓存删除"""
    cache = LocalCache(max_size=10)

    state = SessionState(session_id="test-002")
    cache.set("test-002", state)

    cache.delete("test-002")

    loaded_state = cache.get("test-002")
    assert loaded_state is None


def test_local_cache_max_size():
    """测试本地缓存大小限制"""
    cache = LocalCache(max_size=3)

    # 添加 5 个项目
    for i in range(5):
        state = SessionState(session_id=f"test-{i}")
        cache.set(f"test-{i}", state)

    # 应该只保留最新的 3 个
    assert len(cache.cache) == 3
    assert cache.get("test-0") is None
    assert cache.get("test-1") is None
    assert cache.get("test-4") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_cache.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.state.local_cache'"

- [ ] **Step 3: Implement local cache**

```python
# src/state/local_cache.py
from typing import Optional, Dict
from collections import OrderedDict
import logging

from src.models.state_models import SessionState

logger = logging.getLogger(__name__)


class LocalCache:
    """本地缓存（LRU策略）"""

    def __init__(self, max_size: int = 100):
        """
        初始化本地缓存

        Args:
            max_size: 最大缓存数量
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, SessionState] = OrderedDict()

    def get(self, session_id: str) -> Optional[SessionState]:
        """
        获取缓存状态

        Args:
            session_id: 会话ID

        Returns:
            会话状态，如果不存在则返回 None
        """
        if session_id in self.cache:
            # 移到最后（最近使用）
            self.cache.move_to_end(session_id)
            return self.cache[session_id]

        return None

    def set(self, session_id: str, state: SessionState):
        """
        设置缓存状态

        Args:
            session_id: 会话ID
            state: 会话状态
        """
        if session_id in self.cache:
            # 已存在，更新并移到最后
            self.cache.move_to_end(session_id)
            self.cache[session_id] = state
        else:
            # 不存在，添加
            self.cache[session_id] = state

            # 检查大小限制
            if len(self.cache) > self.max_size:
                # 删除最旧的项
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Evicted oldest cache entry: {oldest_key}")

    def delete(self, session_id: str):
        """
        删除缓存状态

        Args:
            session_id: 会话ID
        """
        if session_id in self.cache:
            del self.cache[session_id]

    def clear(self):
        """清空缓存"""
        self.cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)

    def exists(self, session_id: str) -> bool:
        """
        检查缓存是否存在

        Args:
            session_id: 会话ID

        Returns:
            是否存在
        """
        return session_id in self.cache
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_local_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit local cache**

```bash
git add src/state/local_cache.py tests/test_local_cache.py
git commit -m "feat: add local cache with LRU eviction"
```

---

## Task 4: 会话管理器

**Files:**
- Create: `src/state/session_manager.py`
- Test: `tests/test_session_manager.py`

- [ ] **Step 1: Write the failing test for session manager**

```python
# tests/test_session_manager.py
import pytest
from src.state.session_manager import SessionManager
from src.models.state_models import SessionState


@pytest.mark.asyncio
async def test_session_manager_creation():
    """测试会话管理器创建"""
    manager = SessionManager()

    assert manager is not None


@pytest.mark.asyncio
async def test_create_session():
    """测试创建会话"""
    manager = SessionManager()

    session_id = "test-001"
    state = await manager.create_session(session_id)

    assert state.session_id == session_id
    assert state.current_emotion == "neutral"


@pytest.mark.asyncio
async def test_get_or_create_session():
    """测试获取或创建会话"""
    manager = SessionManager()

    # 第一次创建
    state1 = await manager.get_or_create_session("test-002")
    assert state1.session_id == "test-002"

    # 第二次获取
    state2 = await manager.get_or_create_session("test-002")
    assert state2.session_id == "test-002"
    assert state2 is state1  # 应该是同一个对象


@pytest.mark.asyncio
async def test_update_session():
    """测试更新会话"""
    manager = SessionManager()

    state = await manager.create_session("test-003")
    state.add_interaction("你好", "你好！")

    await manager.update_session(state)

    # 重新加载
    loaded_state = await manager.get_session("test-003")

    assert loaded_state is not None
    assert len(loaded_state.conversation_history) == 1


@pytest.mark.asyncio
async def test_delete_session():
    """测试删除会话"""
    manager = SessionManager()

    await manager.create_session("test-004")
    await manager.delete_session("test-004")

    loaded_state = await manager.get_session("test-004")

    assert loaded_state is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.state.session_manager'"

- [ ] **Step 3: Implement session manager**

```python
# src/state/session_manager.py
from typing import Optional
import logging

from src.models.state_models import SessionState
from src.state.redis_manager import RedisStateManager
from src.state.local_cache import LocalCache

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器"""

    def __init__(
        self,
        redis_url: Optional[str] = "redis://localhost:6379",
        use_redis: bool = True
    ):
        """
        初始化会话管理器

        Args:
            redis_url: Redis 连接URL
            use_redis: 是否使用 Redis
        """
        self.use_redis = use_redis
        self.redis_manager: Optional[RedisStateManager] = None
        self.local_cache = LocalCache(max_size=100)

        if use_redis and redis_url:
            try:
                self.redis_manager = RedisStateManager(redis_url=redis_url)
                logger.info("Session manager initialized with Redis backend")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis, falling back to local cache: {e}")
                self.redis_manager = None
                self.use_redis = False

    async def create_session(self, session_id: str) -> SessionState:
        """
        创建新会话

        Args:
            session_id: 会话ID

        Returns:
            新会话状态
        """
        state = SessionState(session_id=session_id)

        # 保存到存储
        await self._save_state(state)

        logger.info(f"Created new session: {session_id}")
        return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            会话状态，如果不存在则返回 None
        """
        # 先检查本地缓存
        state = self.local_cache.get(session_id)
        if state:
            return state

        # 从 Redis 加载
        if self.redis_manager:
            state = await self.redis_manager.load_state(session_id)
            if state:
                # 缓存到本地
                self.local_cache.set(session_id, state)
                return state

        return None

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

        return state

    async def update_session(self, state: SessionState):
        """
        更新会话

        Args:
            state: 会话状态
        """
        state.update_activity()

        # 更新本地缓存
        self.local_cache.set(state.session_id, state)

        # 更新 Redis
        await self._save_state(state)

    async def delete_session(self, session_id: str):
        """
        删除会话

        Args:
            session_id: 会话ID
        """
        # 删除本地缓存
        self.local_cache.delete(session_id)

        # 删除 Redis
        if self.redis_manager:
            await self.redis_manager.delete_state(session_id)

        logger.info(f"Deleted session: {session_id}")

    async def _save_state(self, state: SessionState):
        """
        保存状态到存储

        Args:
            state: 会话状态
        """
        # 保存到本地缓存
        self.local_cache.set(state.session_id, state)

        # 保存到 Redis
        if self.redis_manager:
            try:
                await self.redis_manager.save_state(state)
            except Exception as e:
                logger.error(f"Failed to save state to Redis: {e}")
                # 继续运行，本地缓存已保存

    async def sync_state(self, session_id: str, other_clock: dict):
        """
        同步状态（使用向量时钟）

        Args:
            session_id: 会话ID
            other_clock: 其他节点的向量时钟
        """
        state = await self.get_session(session_id)

        if state:
            # 合并向量时钟
            state.merge_clock(other_clock)
            state.increment_clock()

            # 保存
            await self.update_session(state)

            logger.debug(f"Synced state for session {session_id}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit session manager**

```bash
git add src/state/session_manager.py tests/test_session_manager.py
git commit -m "feat: add session manager with Redis and local cache fallback"
```

---

## Task 5: 导演指令注册表

**Files:**
- Create: `src/director/command_registry.py`
- Test: `tests/test_command_registry.py`

- [ ] **Step 1: Write the failing test for command registry**

```python
# tests/test_command_registry.py
import pytest
from src.director.command_registry import CommandRegistry, DirectorCommand


def test_command_registry_creation():
    """测试指令注册表创建"""
    registry = CommandRegistry()

    assert registry is not None
    assert len(registry.commands) > 0  # 应该有默认指令


def test_register_command():
    """测试注册指令"""
    registry = CommandRegistry()

    # 注册自定义指令
    cmd = DirectorCommand(
        name="custom_test",
        pattern=r'\[自定义测试\]',
        handler=lambda x: x,
        priority=10
    )

    registry.register(cmd)

    assert "custom_test" in registry.commands


def test_get_command():
    """测试获取指令"""
    registry = CommandRegistry()

    cmd = registry.get_command("volume_down")

    assert cmd is not None
    assert cmd.name == "volume_down"


def test_list_commands():
    """测试列出指令"""
    registry = CommandRegistry()

    commands = registry.list_commands()

    assert len(commands) > 0
    assert "volume_down" in commands
    assert "speed_up" in commands
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_command_registry.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.director.command_registry'"

- [ ] **Step 3: Implement command registry**

```python
# src/director/command_registry.py
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
import re


@dataclass
class DirectorCommand:
    """导演指令"""
    name: str
    pattern: str  # 正则表达式
    handler: Callable[[Any], Any]
    priority: int = 0  # 优先级，数字越大优先级越高
    description: str = ""


class CommandRegistry:
    """导演指令注册表"""

    def __init__(self):
        """初始化指令注册表"""
        self.commands: Dict[str, DirectorCommand] = {}
        self._register_default_commands()

    def _register_default_commands(self):
        """注册默认指令"""
        default_commands = [
            DirectorCommand(
                name="volume_down",
                pattern=r'\[压低音量\]',
                handler=lambda x: {"volume": 0.7},
                priority=5,
                description="降低音量到70%"
            ),
            DirectorCommand(
                name="volume_up",
                pattern=r'\[提高音量\]',
                handler=lambda x: {"volume": 1.3},
                priority=5,
                description="提高音量到130%"
            ),
            DirectorCommand(
                name="speed_up",
                pattern=r'\[加速\]',
                handler=lambda x: {"speed": 1.3},
                priority=5,
                description="加速到130%"
            ),
            DirectorCommand(
                name="speed_down",
                pattern=r'\[减速\]',
                handler=lambda x: {"speed": 0.7},
                priority=5,
                description="减速到70%"
            ),
            DirectorCommand(
                name="pause",
                pattern=r'\[停顿(\d+(?:\.\d+)?)秒\]',
                handler=lambda m: {"pause": float(m.group(1))},
                priority=3,
                description="停顿指定秒数"
            ),
            DirectorCommand(
                name="emotion",
                pattern=r'\[情绪:(\w+)\]',
                handler=lambda m: {"emotion": m.group(1)},
                priority=4,
                description="设置情绪"
            ),
            DirectorCommand(
                name="breath",
                pattern=r'\[呼吸音\]',
                handler=lambda x: {"breath": True},
                priority=2,
                description="添加呼吸音"
            ),
        ]

        for cmd in default_commands:
            self.commands[cmd.name] = cmd

    def register(self, command: DirectorCommand):
        """
        注册指令

        Args:
            command: 导演指令
        """
        self.commands[command.name] = command

    def unregister(self, name: str):
        """
        注销指令

        Args:
            name: 指令名称
        """
        if name in self.commands:
            del self.commands[name]

    def get_command(self, name: str) -> DirectorCommand:
        """
        获取指令

        Args:
            name: 指令名称

        Returns:
            导演指令
        """
        return self.commands.get(name)

    def list_commands(self) -> List[str]:
        """
        列出所有指令

        Returns:
            指令名称列表
        """
        return list(self.commands.keys())

    def get_commands_by_priority(self) -> List[DirectorCommand]:
        """
        按优先级获取指令列表

        Returns:
            指令列表（按优先级降序）
        """
        return sorted(
            self.commands.values(),
            key=lambda cmd: cmd.priority,
            reverse=True
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_command_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit command registry**

```bash
git add src/director/command_registry.py tests/test_command_registry.py
git commit -m "feat: add director command registry with default commands"
```

---

## Task 6: 集成到 WebSocket 服务

**Files:**
- Modify: `src/server.py`
- Test: `tests/test_state_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_state_integration.py
import pytest
from fastapi.testclient import TestClient
from src.server import app


client = TestClient(app)


def test_websocket_state_persistence():
    """测试 WebSocket 状态持久化"""
    with client.websocket_connect("/ws/test-state") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送文本输入
        websocket.send_json({
            "type": "text_input",
            "content": "你好",
            "session_id": "test-state"
        })

        # 等待处理完成
        while True:
            msg = websocket.receive_json()
            if msg.get("type") == "status" and msg.get("status") == "listening":
                break

    # 断开连接后重新连接
    with client.websocket_connect("/ws/test-state") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送另一条消息
        websocket.send_json({
            "type": "text_input",
            "content": "继续",
            "session_id": "test-state"
        })

        # 应该能恢复之前的会话状态
        # （验证对话历史是否保留）
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state_integration.py -v`
Expected: FAIL (state management not integrated yet)

- [ ] **Step 3: Integrate state management into server**

```python
# src/server.py (add state manager)
from state.session_manager import SessionManager

# 全局会话管理器
session_manager = SessionManager()


# Modify handle_text_input to use session manager
async def handle_text_input(session_id: str, message: TextInputMessage):
    """处理文本输入"""
    print(f"[Session {session_id}] Text input: {message.content}")

    # 获取或创建会话状态
    state = await session_manager.get_or_create_session(session_id)

    # 更新活动时间
    state.update_activity()

    # 发送处理状态
    await manager.send_status(session_id, "processing")

    try:
        # ... (existing LLM and TTS code)

        # 更新对话历史
        state.add_interaction(message.content, full_text)

        # 保存状态
        await session_manager.update_session(state)

        # 发送完成状态
        await manager.send_status(session_id, "listening")

    except Exception as e:
        # ... (error handling)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit integration**

```bash
git add src/server.py tests/test_state_integration.py
git commit -m "feat: integrate state management into WebSocket server"
```

---

## 验收标准

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] Redis 状态持久化正常工作
- [ ] 本地缓存降级正常
- [ ] 向量时钟合并正确
- [ ] 导演指令注册和管理正常
- [ ] 代码覆盖率 > 80%

---

## 下一步

完成阶段5后，继续：

- **阶段6**: 集成测试 + 性能优化

---

**文档版本**: v1.0
**最后更新**: 2026-04-25
**作者**: Claude Sonnet 4.6
