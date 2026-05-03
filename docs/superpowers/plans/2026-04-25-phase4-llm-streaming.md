# LLM 流式生成模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成 Claude API 实现流式文本生成，支持上下文管理和提示词工程，首字延迟 < 200ms。

**Architecture:** 使用 Anthropic SDK 进行流式生成，通过 LLM 路由器选择本地/云端模型，支持实时打断和上下文注入。

**Tech Stack:** Python 3.11.4, Anthropic SDK 0.97.0, asyncio

---

## 文件结构

```
O:\AII\app\references\
├── src/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── claude_client.py        # Claude API 客户端
│   │   ├── llm_router.py           # LLM 路由器
│   │   ├── prompt_templates.py     # 提示词模板
│   │   └── context_manager.py      # 上下文管理器
│   └── models/
│       └── llm_config.py           # LLM 配置模型
├── tests/
│   ├── test_claude_client.py       # Claude 客户端测试
│   ├── test_llm_router.py          # 路由器测试
│   ├── test_prompt_templates.py    # 提示词测试
│   └── test_context_manager.py     # 上下文管理测试
└── docs/
    └── llm_integration.md          # LLM 集成文档
```

---

## Task 1: LLM 配置模型

**Files:**
- Create: `src/models/llm_config.py`
- Test: `tests/test_llm_config.py`

- [ ] **Step 1: Write the failing test for LLM config**

```python
# tests/test_llm_config.py
import pytest
from src.models.llm_config import LLMConfig, ModelType


def test_llm_config_creation():
    """测试 LLM 配置创建"""
    config = LLMConfig(
        model_type=ModelType.CLAUDE,
        model_name="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0.8
    )

    assert config.model_type == ModelType.CLAUDE
    assert config.model_name == "claude-sonnet-4-6"
    assert config.max_tokens == 500
    assert config.temperature == 0.8


def test_llm_config_default_values():
    """测试默认值"""
    config = LLMConfig()

    assert config.model_type == ModelType.CLAUDE
    assert config.max_tokens == 500
    assert config.temperature == 0.7


def test_model_type_enum():
    """测试模型类型枚举"""
    assert ModelType.CLAUDE.value == "claude"
    assert ModelType.QWEN_LOCAL.value == "qwen_local"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models.llm_config'"

- [ ] **Step 3: Implement LLM config models**

```python
# src/models/llm_config.py
from enum import Enum
from pydantic import BaseModel, Field


class ModelType(Enum):
    """模型类型"""
    CLAUDE = "claude"
    QWEN_LOCAL = "qwen_local"


class LLMConfig(BaseModel):
    """LLM 配置"""
    model_type: ModelType = ModelType.CLAUDE
    model_name: str = "claude-sonnet-4-6"
    max_tokens: int = Field(500, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)

    # Claude 特定参数
    system_prompt: str = "你是一个温暖的故事讲述者。"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit LLM config**

```bash
git add src/models/llm_config.py tests/test_llm_config.py
git commit -m "feat: add LLM configuration models"
```

---

## Task 2: 提示词模板

**Files:**
- Create: `src/llm/prompt_templates.py`
- Test: `tests/test_prompt_templates.py`

- [ ] **Step 1: Write the failing test for prompt templates**

```python
# tests/test_prompt_templates.py
import pytest
from src.llm.prompt_templates import PromptTemplates


def test_narrative_generation_template():
    """测试叙事生成模板"""
    template = PromptTemplates.narrative_generation(
        user_input="我想听一个睡前故事",
        emotion="平静",
        context={"scene": "夜晚"}
    )

    assert "睡前故事" in template
    assert "平静" in template
    assert len(template) > 50


def test_emotion_response_template():
    """测试情绪响应模板"""
    template = PromptTemplates.emotion_response(
        user_emotion="开心",
        context={"previous_emotion": "平静"}
    )

    assert "开心" in template
    assert len(template) > 30


def test_branch_decision_template():
    """测试剧情分支模板"""
    template = PromptTemplates.branch_decision(
        current_scene="森林",
        options=["继续前进", "返回", "休息"]
    )

    assert "森林" in template
    assert "继续前进" in template
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompt_templates.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.llm.prompt_templates'"

- [ ] **Step 3: Implement prompt templates**

```python
# src/llm/prompt_templates.py
from typing import Dict, List, Optional


class PromptTemplates:
    """提示词模板集合"""

    @staticmethod
    def narrative_generation(
        user_input: str,
        emotion: str = "neutral",
        context: Optional[Dict] = None
    ) -> str:
        """
        叙事生成模板

        Args:
            user_input: 用户输入
            emotion: 当前情绪
            context: 上下文信息

        Returns:
            完整提示词
        """
        context_str = ""
        if context:
            context_str = f"\n当前场景: {context.get('scene', '未知')}"

        return f"""你是一个温暖的故事讲述者，正在与用户进行互动叙事。

用户说："{user_input}"
当前情绪：{emotion}{context_str}

请用简短、温暖的话回应（不超过50字），可以：
- 继续故事情节
- 询问用户选择
- 表达情感共鸣

回应："""

    @staticmethod
    def emotion_response(
        user_emotion: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        情绪响应模板

        Args:
            user_emotion: 用户情绪
            context: 上下文信息

        Returns:
            完整提示词
        """
        previous_emotion = ""
        if context and "previous_emotion" in context:
            previous_emotion = f"（之前情绪：{context['previous_emotion']}）"

        return f"""用户当前情绪：{user_emotion}{previous_emotion}

请用简短的话表达理解和共鸣（不超过30字）："""

    @staticmethod
    def branch_decision(
        current_scene: str,
        options: List[str]
    ) -> str:
        """
        剧情分支模板

        Args:
            current_scene: 当前场景
            options: 可选项列表

        Returns:
            完整提示词
        """
        options_str = "、".join(options)

        return f"""当前场景：{current_scene}

用户可以选择：
{options_str}

请描述当前情况并引导用户做出选择（不超过40字）："""

    @staticmethod
    def system_prompt() -> str:
        """系统提示词"""
        return """你是一个温暖、富有同理心的故事讲述者。你的特点是：
- 语言简洁、温暖
- 善于倾听和回应
- 能够根据用户情绪调整语气
- 创造引人入胜的故事情节

请始终保持友好和专业的态度。"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompt_templates.py -v`
Expected: PASS

- [ ] **Step 5: Commit prompt templates**

```bash
git add src/llm/prompt_templates.py tests/test_prompt_templates.py
git commit -m "feat: add prompt templates for narrative generation"
```

---

## Task 3: 上下文管理器

**Files:**
- Create: `src/llm/context_manager.py`
- Test: `tests/test_context_manager.py`

- [ ] **Step 1: Write the failing test for context manager**

```python
# tests/test_context_manager.py
import pytest
from src.llm.context_manager import ContextManager


def test_context_manager_creation():
    """测试上下文管理器创建"""
    manager = ContextManager(max_history=10)

    assert manager.max_history == 10
    assert len(manager.history) == 0


def test_add_message():
    """测试添加消息"""
    manager = ContextManager(max_history=5)

    manager.add_message("user", "你好")
    manager.add_message("assistant", "你好！")

    assert len(manager.history) == 2
    assert manager.history[0]["role"] == "user"
    assert manager.history[1]["role"] == "assistant"


def test_max_history_limit():
    """测试历史记录限制"""
    manager = ContextManager(max_history=3)

    # 添加 5 条消息
    for i in range(5):
        manager.add_message("user", f"消息 {i}")

    # 应该只保留最新的 3 条
    assert len(manager.history) == 3
    assert "消息 2" in manager.history[0]["content"]
    assert "消息 4" in manager.history[2]["content"]


def test_get_context_for_llm():
    """测试获取 LLM 上下文"""
    manager = ContextManager()

    manager.add_message("user", "你好")
    manager.add_message("assistant", "你好！")

    context = manager.get_context_for_llm()

    assert len(context) == 2
    assert context[0]["role"] == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.llm.context_manager'"

- [ ] **Step 3: Implement context manager**

```python
# src/llm/context_manager.py
from typing import List, Dict
from collections import deque
import time


class ContextManager:
    """上下文管理器"""

    def __init__(self, max_history: int = 10):
        """
        初始化上下文管理器

        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """
        添加消息到历史记录

        Args:
            role: 角色 ('user' 或 'assistant')
            content: 消息内容
            metadata: 元数据
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }

        self.history.append(message)

    def get_context_for_llm(self) -> List[Dict]:
        """
        获取 LLM 上下文

        Returns:
            消息列表（适合 LLM API 格式）
        """
        return [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in self.history
        ]

    def get_recent_messages(self, n: int = 5) -> List[Dict]:
        """
        获取最近的 n 条消息

        Args:
            n: 消息数量

        Returns:
            消息列表
        """
        recent = list(self.history)[-n:]
        return recent

    def clear(self):
        """清空历史记录"""
        self.history.clear()

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计数据
        """
        user_messages = sum(1 for msg in self.history if msg["role"] == "user")
        assistant_messages = sum(1 for msg in self.history if msg["role"] == "assistant")

        return {
            "total_messages": len(self.history),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "max_history": self.max_history
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit context manager**

```bash
git add src/llm/context_manager.py tests/test_context_manager.py
git commit -m "feat: add context manager for conversation history"
```

---

## Task 4: Claude API 客户端

**Files:**
- Create: `src/llm/claude_client.py`
- Test: `tests/test_claude_client.py`

- [ ] **Step 1: Write the failing test for Claude client**

```python
# tests/test_claude_client.py
import pytest
import asyncio
from src.llm.claude_client import ClaudeClient
from src.models.llm_config import LLMConfig


@pytest.mark.asyncio
async def test_claude_client_creation():
    """测试 Claude 客户端创建"""
    config = LLMConfig()
    client = ClaudeClient(config)

    assert client.config == config


@pytest.mark.asyncio
async def test_generate_stream():
    """测试流式生成"""
    config = LLMConfig(max_tokens=100)
    client = ClaudeClient(config)

    # 流式生成
    text_chunks = []
    async for chunk in client.generate_stream("你好"):
        text_chunks.append(chunk)

    # 验证生成了文本
    assert len(text_chunks) > 0
    full_text = "".join(text_chunks)
    assert len(full_text) > 0


@pytest.mark.asyncio
async def test_generate_with_context():
    """测试带上下文的生成"""
    config = LLMConfig()
    client = ClaudeClient(config)

    context = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！"}
    ]

    text_chunks = []
    async for chunk in client.generate_stream("今天天气怎么样？", context=context):
        text_chunks.append(chunk)

    assert len(text_chunks) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_claude_client.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.llm.claude_client'"

- [ ] **Step 3: Implement Claude client**

```python
# src/llm/claude_client.py
import anthropic
import asyncio
from typing import AsyncIterator, List, Dict, Optional
import os
import logging

from src.models.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude API 客户端"""

    def __init__(self, config: LLMConfig):
        """
        初始化 Claude 客户端

        Args:
            config: LLM 配置
        """
        self.config = config

        # 初始化 Anthropic 客户端
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=api_key)

    async def generate_stream(
        self,
        prompt: str,
        context: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        流式生成文本

        Args:
            prompt: 用户提示词
            context: 对话上下文
            system_prompt: 系统提示词

        Yields:
            文本块
        """
        # 构建消息列表
        messages = []

        # 添加上下文
        if context:
            messages.extend(context)

        # 添加当前提示词
        messages.append({"role": "user", "content": prompt})

        # 使用配置的系统提示词
        system = system_prompt or self.config.system_prompt

        logger.info(f"Generating text with Claude: {prompt[:50]}...")

        try:
            # 流式生成
            with self.client.messages.stream(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        context: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        生成完整文本

        Args:
            prompt: 用户提示词
            context: 对话上下文
            system_prompt: 系统提示词

        Returns:
            完整文本
        """
        full_text = []
        async for chunk in self.generate_stream(prompt, context, system_prompt):
            full_text.append(chunk)

        return "".join(full_text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_claude_client.py -v`
Expected: PASS (requires ANTHROPIC_API_KEY)

- [ ] **Step 5: Commit Claude client**

```bash
git add src/llm/claude_client.py tests/test_claude_client.py
git commit -m "feat: add Claude API client with streaming support"
```

---

## Task 5: LLM 路由器

**Files:**
- Create: `src/llm/llm_router.py`
- Test: `tests/test_llm_router.py`

- [ ] **Step 1: Write the failing test for LLM router**

```python
# tests/test_llm_router.py
import pytest
from src.llm.llm_router import LLMRouter
from src.models.llm_config import LLMConfig, ModelType


@pytest.mark.asyncio
async def test_llm_router_creation():
    """测试 LLM 路由器创建"""
    config = LLMConfig()
    router = LLMRouter(config)

    assert router.config == config


@pytest.mark.asyncio
async def test_route_to_claude():
    """测试路由到 Claude"""
    config = LLMConfig(model_type=ModelType.CLAUDE)
    router = LLMRouter(config)

    # 简单响应任务
    text_chunks = []
    async for chunk in router.route_and_generate(
        "simple_response",
        "你好"
    ):
        text_chunks.append(chunk)

    assert len(text_chunks) > 0


@pytest.mark.asyncio
async def test_route_by_task_type():
    """测试按任务类型路由"""
    config = LLMConfig()
    router = LLMRouter(config)

    # 节奏控制任务（应该路由到本地模型，如果可用）
    task_type = "rhythm_control"

    # 剧情生成任务（应该路由到云端）
    task_type = "plot_generation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_router.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.llm.llm_router'"

- [ ] **Step 3: Implement LLM router**

```python
# src/llm/llm_router.py
from typing import AsyncIterator, Optional, List, Dict
import logging

from src.models.llm_config import LLMConfig, ModelType
from src.llm.claude_client import ClaudeClient
from src.llm.context_manager import ContextManager
from src.llm.prompt_templates import PromptTemplates
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 路由器"""

    def __init__(
        self,
        config: LLMConfig,
        context_manager: Optional[ContextManager] = None,
        interrupt_handler: Optional[InterruptHandler] = None
    ):
        """
        初始化 LLM 路由器

        Args:
            config: LLM 配置
            context_manager: 上下文管理器
            interrupt_handler: 打断处理器
        """
        self.config = config
        self.context_manager = context_manager or ContextManager()
        self.interrupt_handler = interrupt_handler

        # 初始化客户端
        self.claude_client = None
        if config.model_type == ModelType.CLAUDE:
            self.claude_client = ClaudeClient(config)

    async def route_and_generate(
        self,
        task_type: str,
        prompt: str,
        context: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        根据任务类型路由并生成文本

        Args:
            task_type: 任务类型
            prompt: 提示词
            context: 上下文信息

        Yields:
            文本块
        """
        # 根据任务类型选择模型
        if task_type in ["rhythm_control", "simple_response", "emotion_ack"]:
            # 简单任务：使用配置的模型
            model_type = self.config.model_type
        elif task_type in ["plot_generation", "creative_narrative", "branch_decision"]:
            # 复杂任务：强制使用云端模型
            model_type = ModelType.CLAUDE
        else:
            model_type = self.config.model_type

        logger.info(f"Routing task '{task_type}' to {model_type.value}")

        # 生成文本
        if model_type == ModelType.CLAUDE:
            async for chunk in self._generate_with_claude(prompt, context):
                # 检查打断
                if self.interrupt_handler:
                    await self.interrupt_handler.check_and_raise()

                yield chunk
        else:
            # 本地模型（暂未实现）
            raise NotImplementedError("Local model not implemented yet")

    async def _generate_with_claude(
        self,
        prompt: str,
        context: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """
        使用 Claude 生成文本

        Args:
            prompt: 提示词
            context: 上下文信息

        Yields:
            文本块
        """
        if not self.claude_client:
            self.claude_client = ClaudeClient(self.config)

        # 获取对话上下文
        conversation_context = self.context_manager.get_context_for_llm()

        # 流式生成
        async for chunk in self.claude_client.generate_stream(
            prompt,
            context=conversation_context
        ):
            yield chunk

        # 添加到上下文
        self.context_manager.add_message("user", prompt)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit LLM router**

```bash
git add src/llm/llm_router.py tests/test_llm_router.py
git commit -m "feat: add LLM router with task-based routing"
```

---

## Task 6: 集成到 WebSocket 服务

**Files:**
- Modify: `src/server.py`
- Test: `tests/test_llm_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_llm_integration.py
import pytest
from fastapi.testclient import TestClient
from src.server import app


client = TestClient(app)


def test_websocket_llm_integration():
    """测试 WebSocket 与 LLM 集成"""
    with client.websocket_connect("/ws/test-llm") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送文本输入
        websocket.send_json({
            "type": "text_input",
            "content": "请讲一个故事",
            "session_id": "test-llm"
        })

        # 接收状态更新
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 接收文本流
        text_chunks = []
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "text_chunk":
                text_chunks.append(msg["content"])
                if msg["is_final"]:
                    break

        # 验证生成了文本
        assert len(text_chunks) > 0
        full_text = "".join(text_chunks)
        assert len(full_text) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_integration.py -v`
Expected: FAIL (LLM not integrated yet)

- [ ] **Step 3: Integrate LLM into server**

```python
# src/server.py (modify handle_text_input function)
from llm.llm_router import LLMRouter
from llm.context_manager import ContextManager
from models.llm_config import LLMConfig

# 全局 LLM 路由器
llm_config = LLMConfig()
llm_routers = {}
context_managers = {}


async def handle_text_input(session_id: str, message: TextInputMessage):
    """处理文本输入"""
    print(f"[Session {session_id}] Text input: {message.content}")

    # 更新状态
    state = manager.get_session_state(session_id)
    if state:
        state.update_activity()

    # 发送处理状态
    await manager.send_status(session_id, "processing")

    try:
        # 创建或获取 LLM 路由器
        if session_id not in llm_routers:
            context_manager = ContextManager()
            interrupt_handler = interrupt_handlers.get(session_id)
            llm_routers[session_id] = LLMRouter(
                llm_config,
                context_manager,
                interrupt_handler
            )
            context_managers[session_id] = context_manager

        router = llm_routers[session_id]

        # 流式生成文本
        full_text = ""
        async for chunk in router.route_and_generate(
            "narrative_generation",
            message.content
        ):
            full_text += chunk

            # 发送文本块
            await manager.send_text_chunk(session_id, chunk, is_final=False)

        # 发送结束标记
        await manager.send_text_chunk(session_id, "", is_final=True)

        # 更新对话历史
        if state:
            state.add_interaction(message.content, full_text)

        # 发送完成状态
        await manager.send_status(session_id, "speaking")

    except VADInterruptException:
        print(f"[Session {session_id}] LLM interrupted")
        await manager.send_status(session_id, "listening")

    except Exception as e:
        print(f"[Session {session_id}] LLM error: {e}")
        await manager.send_error(
            session_id,
            "LLM_ERROR",
            str(e),
            recoverable=True
        )
        await manager.send_status(session_id, "listening")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit integration**

```bash
git add src/server.py tests/test_llm_integration.py
git commit -m "feat: integrate LLM into WebSocket server"
```

---

## Task 7: 性能测试

**Files:**
- Create: `tests/test_llm_performance.py`

- [ ] **Step 1: Write performance test**

```python
# tests/test_llm_performance.py
import pytest
import asyncio
import time
from src.llm.llm_router import LLMRouter
from src.models.llm_config import LLMConfig


@pytest.mark.asyncio
async def test_llm_first_token_latency():
    """测试首字延迟"""
    config = LLMConfig()
    router = LLMRouter(config)

    # 测试提示词
    prompt = "你好"

    # 测量首字延迟
    start = time.perf_counter()
    first_token_time = None

    async for chunk in router.route_and_generate("simple_response", prompt):
        if first_token_time is None:
            first_token_time = time.perf_counter() - start
            break

    print(f"\nLLM First Token Latency: {first_token_time * 1000:.2f} ms")

    # 验证延迟 < 200ms
    assert first_token_time < 0.2, f"First token latency {first_token_time}s exceeds 200ms"


@pytest.mark.asyncio
async def test_llm_throughput():
    """测试 LLM 吞吐量"""
    config = LLMConfig()
    router = LLMRouter(config)

    # 测试长提示词
    prompt = "请讲一个故事" * 5

    start = time.perf_counter()
    token_count = 0

    async for chunk in router.route_and_generate("plot_generation", prompt):
        token_count += len(chunk)

    end = time.perf_counter()
    duration = end - start

    print(f"\nLLM Throughput:")
    print(f"  Total tokens: {token_count}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Tokens/second: {token_count / duration:.2f}")
```

- [ ] **Step 2: Run performance test**

Run: `pytest tests/test_llm_performance.py -v -s`
Expected: PASS with performance metrics printed

- [ ] **Step 3: Commit performance tests**

```bash
git add tests/test_llm_performance.py
git commit -m "test: add LLM performance tests"
```

---

## 验收标准

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 性能测试通过（首字延迟 < 200ms）
- [ ] 提示词模板正确应用
- [ ] 上下文管理正常工作
- [ ] 打断机制正常工作
- [ ] 代码覆盖率 > 80%

---

## 下一步

完成阶段4后，继续：

- **阶段5**: 状态管理 + 导演指令模块
- **阶段6**: 集成测试 + 性能优化

---

**文档版本**: v1.0
**最后更新**: 2026-04-25
**作者**: Claude Sonnet 4.6
