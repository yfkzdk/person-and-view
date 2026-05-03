# 实时流式语音叙事系统 - 阶段1设计文档

> **系统架构 + WebSocket 双向通信模块**

**目标**: 建立系统整体架构和 WebSocket 双向通信基础，实现音频流的双向传输。

**架构**: 单进程 Asyncio 架构，FastAPI 提供 WebSocket 服务，支持音频流双向传输和会话管理。

**技术栈**: Python 3.11.4, FastAPI, Uvicorn, WebSockets, Redis

---

## 一、系统整体架构设计

### 1.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     单进程 Asyncio 应用                       │
├─────────────────────────────────────────────────────────────┤
│  WebSocket Server (FastAPI)                                 │
│    ↓ ↑ 双向音频流                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NarrativeOrchestrator (中央协调器)                   │   │
│  │    ├─ VADMonitor (Silero VAD) — 语音检测             │   │
│  │    ├─ EmotionClassifier — 情绪识别                   │   │
│  │    ├─ LLMRouter — 本地/云端 LLM 路由                 │   │
│  │    ├─ TTSStreamer (Edge TTS) — 流式语音合成          │   │
│  │    ├─ DirectorParser — 导演指令解析                  │   │
│  │    └─ StateManager (Redis) — 状态持久化              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ↓ ↑                                                         │
│  Redis Stream (事件队列)                                     │
│    ├─ narration_events (剧情节点)                            │
│    ├─ user_interactions (用户行为)                           │
│    └─ system_commands (导演指令)                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 模块划分与职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **WebSocket Server** | 双向音频流传输 | 音频字节流 | 音频字节流 + JSON 控制消息 |
| **NarrativeOrchestrator** | 中央协调，任务调度 | 用户输入 + 状态 | 叙事文本 + 音频 |
| **VADMonitor** | 语音活动检测 | 音频块 | 布尔值（是否语音） |
| **EmotionClassifier** | 情绪识别 | 音频块 | 情绪标签 |
| **LLMRouter** | LLM 路由与生成 | 提示词 + 上下文 | 文本流 |
| **TTSStreamer** | 流式语音合成 | 文本流 | 音频流 |
| **DirectorParser** | 导演指令解析 | 文本 | 控制向量 |
| **StateManager** | 状态持久化 | 状态对象 | 状态对象 |

### 1.3 数据流与控制流

#### 正常流程（无打断）

```
用户语音输入
  → WebSocket 接收音频字节流
  → VAD 检测语音活动
  → 情绪识别
  → LLM 生成叙事文本（流式）
  → 导演指令解析
  → TTS 流式合成音频
  → WebSocket 发送音频字节流
  → 用户听到响应
```

#### 打断流程

```
用户语音输入
  → WebSocket 接收音频字节流
  → VAD 检测到用户开始说话
  → 触发 VADInterruptException
  → 取消当前 TTS + LLM 任务
  → 清理音频缓冲区
  → 重新开始接收用户输入
```

### 1.4 技术栈选型理由

| 技术 | 选型理由 |
|------|---------|
| **Python 3.11+** | asyncio 原生支持，性能优化，类型提示完善 |
| **FastAPI** | 高性能异步框架，原生 WebSocket 支持，自动文档 |
| **Uvicorn** | ASGI 服务器，支持 HTTP/2，性能优异 |
| **Silero VAD** | 无需编译，延迟 < 1ms，准确率高，预训练模型 |
| **Edge TTS** | 免费使用，流式输出，多语言支持，低延迟 |
| **Anthropic SDK** | 官方 SDK，流式生成，稳定可靠 |
| **Redis** | 高性能状态存储，支持 Stream，持久化 |
| **PyTorch** | Silero VAD 依赖，CPU 版本足够 |

---

## 二、WebSocket 双向通信模块设计

### 2.1 模块职责

- 建立 WebSocket 连接
- 接收用户音频流（字节流）
- 发送 AI 音频流（字节流）
- 发送/接收控制消息（JSON）
- 会话管理（连接、断开、重连）
- 错误处理与降级

### 2.2 WebSocket 消息协议

#### 客户端 → 服务端

**音频数据消息**:
```json
{
  "type": "audio",
  "data": "<base64-encoded-audio-bytes>",
  "timestamp": 1620000000.123,
  "session_id": "session-001"
}
```

**文本输入消息**:
```json
{
  "type": "text_input",
  "content": "你好，请讲一个故事",
  "session_id": "session-001"
}
```

**控制消息**:
```json
{
  "type": "control",
  "action": "interrupt" | "pause" | "resume" | "stop",
  "session_id": "session-001"
}
```

#### 服务端 → 客户端

**音频数据消息**:
```json
{
  "type": "audio",
  "data": "<base64-encoded-audio-bytes>",
  "timestamp": 1620000000.456
}
```

**文本流消息**:
```json
{
  "type": "text_chunk",
  "content": "很久以前",
  "is_final": false
}
```

**状态消息**:
```json
{
  "type": "status",
  "status": "processing" | "speaking" | "listening" | "idle",
  "session_id": "session-001"
}
```

**错误消息**:
```json
{
  "type": "error",
  "error_code": "VAD_ERROR",
  "message": "语音检测失败",
  "recoverable": true
}
```

### 2.3 文件结构

```
O:\AII\app\references\
├── src/
│   ├── __init__.py
│   ├── server.py                    # FastAPI 应用入口
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── connection_manager.py    # WebSocket 连接管理
│   │   ├── message_handler.py       # 消息处理
│   │   └── session.py               # 会话管理
│   ├── models/
│   │   ├── __init__.py
│   │   ├── messages.py              # 消息模型定义
│   │   └── session_state.py         # 会话状态模型
│   └── utils/
│       ├── __init__.py
│       └── audio_utils.py           # 音频处理工具
├── tests/
│   ├── __init__.py
│   ├── test_websocket.py            # WebSocket 测试
│   └── test_connection_manager.py   # 连接管理测试
└── docs/
    └── api/
        └── websocket_protocol.md    # WebSocket 协议文档
```

---

## 三、核心代码实现

### 3.1 消息模型定义

**文件**: `src/models/messages.py`

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class AudioMessage(BaseModel):
    """音频数据消息"""
    type: Literal["audio"] = "audio"
    data: str  # base64-encoded
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    session_id: Optional[str] = None


class TextInputMessage(BaseModel):
    """文本输入消息"""
    type: Literal["text_input"] = "text_input"
    content: str
    session_id: str


class ControlMessage(BaseModel):
    """控制消息"""
    type: Literal["control"] = "control"
    action: Literal["interrupt", "pause", "resume", "stop"]
    session_id: str


class TextChunkMessage(BaseModel):
    """文本流消息"""
    type: Literal["text_chunk"] = "text_chunk"
    content: str
    is_final: bool = False


class StatusMessage(BaseModel):
    """状态消息"""
    type: Literal["status"] = "status"
    status: Literal["processing", "speaking", "listening", "idle"]
    session_id: str


class ErrorMessage(BaseModel):
    """错误消息"""
    type: Literal["error"] = "error"
    error_code: str
    message: str
    recoverable: bool = True
```

### 3.2 会话状态模型

**文件**: `src/models/session_state.py`

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


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

    # 统计信息
    total_interactions: int = 0
    total_audio_sent: int = 0  # bytes
    total_audio_received: int = 0  # bytes

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
```

### 3.3 WebSocket 连接管理器

**文件**: `src/websocket/connection_manager.py`

```python
from fastapi import WebSocket
from typing import Dict, Optional
import asyncio
import json
from datetime import datetime

from models.session_state import SessionState
from models.messages import (
    AudioMessage,
    TextInputMessage,
    ControlMessage,
    TextChunkMessage,
    StatusMessage,
    ErrorMessage
)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # session_id -> SessionState
        self.session_states: Dict[str, SessionState] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """接受新连接"""
        await websocket.accept()

        self.active_connections[session_id] = websocket

        # 创建或恢复会话状态
        if session_id not in self.session_states:
            self.session_states[session_id] = SessionState(session_id=session_id)
        else:
            # 恢复会话，更新活动时间
            self.session_states[session_id].update_activity()

        print(f"[{datetime.now()}] Session {session_id} connected")

        # 发送连接成功消息
        await self.send_status(session_id, "listening")

    def disconnect(self, session_id: str):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

        print(f"[{datetime.now()}] Session {session_id} disconnected")

    async def send_audio(self, session_id: str, audio_data: bytes):
        """发送音频数据"""
        if session_id not in self.active_connections:
            return

        import base64
        message = AudioMessage(
            data=base64.b64encode(audio_data).decode('utf-8'),
            session_id=session_id
        )

        await self.active_connections[session_id].send_json(message.dict())

        # 更新统计
        self.session_states[session_id].total_audio_sent += len(audio_data)

    async def send_text_chunk(self, session_id: str, content: str, is_final: bool = False):
        """发送文本块"""
        if session_id not in self.active_connections:
            return

        message = TextChunkMessage(content=content, is_final=is_final)
        await self.active_connections[session_id].send_json(message.dict())

    async def send_status(self, session_id: str, status: str):
        """发送状态消息"""
        if session_id not in self.active_connections:
            return

        message = StatusMessage(status=status, session_id=session_id)
        await self.active_connections[session_id].send_json(message.dict())

    async def send_error(self, session_id: str, error_code: str, message: str, recoverable: bool = True):
        """发送错误消息"""
        if session_id not in self.active_connections:
            return

        error_msg = ErrorMessage(
            error_code=error_code,
            message=message,
            recoverable=recoverable
        )
        await self.active_connections[session_id].send_json(error_msg.dict())

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        return self.session_states.get(session_id)
```

### 3.4 WebSocket 服务端

**文件**: `src/server.py`

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json
import base64

from websocket.connection_manager import ConnectionManager
from models.messages import AudioMessage, TextInputMessage, ControlMessage

app = FastAPI(title="Real-time Voice Narrative System")
manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 端点"""
    await manager.connect(websocket, session_id)

    try:
        while True:
            # 接收消息
            raw_message = await websocket.receive()

            # 处理文本消息
            if "text" in raw_message:
                message_data = json.loads(raw_message["text"])
                message_type = message_data.get("type")

                if message_type == "text_input":
                    # 处理文本输入
                    message = TextInputMessage(**message_data)
                    await handle_text_input(session_id, message)

                elif message_type == "control":
                    # 处理控制消息
                    message = ControlMessage(**message_data)
                    await handle_control(session_id, message)

            # 处理二进制消息（音频）
            elif "bytes" in raw_message:
                audio_data = raw_message["bytes"]
                await handle_audio_input(session_id, audio_data)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"Session {session_id} disconnected normally")

    except Exception as e:
        print(f"Session {session_id} error: {e}")
        await manager.send_error(
            session_id,
            "CONNECTION_ERROR",
            str(e),
            recoverable=False
        )
        manager.disconnect(session_id)


async def handle_text_input(session_id: str, message: TextInputMessage):
    """处理文本输入"""
    print(f"[Session {session_id}] Text input: {message.content}")

    # 更新状态
    state = manager.get_session_state(session_id)
    if state:
        state.update_activity()

    # TODO: 调用 LLM 生成响应（阶段4实现）
    # 临时响应
    await manager.send_status(session_id, "processing")
    await asyncio.sleep(0.5)  # 模拟处理延迟
    await manager.send_text_chunk(session_id, f"收到: {message.content}", is_final=True)
    await manager.send_status(session_id, "listening")


async def handle_audio_input(session_id: str, audio_data: bytes):
    """处理音频输入"""
    # 更新统计
    state = manager.get_session_state(session_id)
    if state:
        state.total_audio_received += len(audio_data)

    # TODO: 调用 VAD 检测（阶段2实现）
    # 临时处理：直接回传
    await manager.send_audio(session_id, audio_data)


async def handle_control(session_id: str, message: ControlMessage):
    """处理控制消息"""
    print(f"[Session {session_id}] Control: {message.action}")

    if message.action == "interrupt":
        # TODO: 实现打断逻辑（阶段2实现）
        await manager.send_status(session_id, "listening")

    elif message.action == "pause":
        await manager.send_status(session_id, "idle")

    elif message.action == "resume":
        await manager.send_status(session_id, "listening")

    elif message.action == "stop":
        await manager.send_status(session_id, "idle")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 四、测试策略

### 4.1 单元测试

**文件**: `tests/test_connection_manager.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from websocket.connection_manager import ConnectionManager
from models.session_state import SessionState


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.mark.asyncio
async def test_connect_creates_session(manager):
    """测试连接创建会话"""
    websocket = AsyncMock()
    session_id = "test-session-001"

    await manager.connect(websocket, session_id)

    assert session_id in manager.active_connections
    assert session_id in manager.session_states
    assert manager.session_states[session_id].session_id == session_id


@pytest.mark.asyncio
async def test_send_audio(manager):
    """测试发送音频"""
    websocket = AsyncMock()
    session_id = "test-session-001"

    await manager.connect(websocket, session_id)

    audio_data = b"test_audio_data"
    await manager.send_audio(session_id, audio_data)

    # 验证发送了消息
    assert websocket.send_json.called

    # 验证统计更新
    assert manager.session_states[session_id].total_audio_sent == len(audio_data)


@pytest.mark.asyncio
async def test_send_text_chunk(manager):
    """测试发送文本块"""
    websocket = AsyncMock()
    session_id = "test-session-001"

    await manager.connect(websocket, session_id)

    await manager.send_text_chunk(session_id, "Hello", is_final=False)

    assert websocket.send_json.called


@pytest.mark.asyncio
async def test_disconnect(manager):
    """测试断开连接"""
    websocket = AsyncMock()
    session_id = "test-session-001"

    await manager.connect(websocket, session_id)
    manager.disconnect(session_id)

    assert session_id not in manager.active_connections
```

### 4.2 集成测试

**文件**: `tests/test_websocket.py`

```python
import pytest
from fastapi.testclient import TestClient
from server import app
import json
import base64


client = TestClient(app)


def test_websocket_connect():
    """测试 WebSocket 连接"""
    with client.websocket_connect("/ws/test-session") as websocket:
        # 连接成功后应该收到状态消息
        data = websocket.receive_json()
        assert data["type"] == "status"
        assert data["status"] == "listening"


def test_websocket_text_input():
    """测试文本输入"""
    with client.websocket_connect("/ws/test-session") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送文本输入
        message = {
            "type": "text_input",
            "content": "你好",
            "session_id": "test-session"
        }
        websocket.send_json(message)

        # 接收状态更新
        status = websocket.receive_json()
        assert status["type"] == "status"
        assert status["status"] == "processing"

        # 接收文本响应
        response = websocket.receive_json()
        assert response["type"] == "text_chunk"


def test_websocket_audio():
    """测试音频传输"""
    with client.websocket_connect("/ws/test-session") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送音频数据
        audio_data = b"test_audio_bytes"
        websocket.send_bytes(audio_data)

        # 接收回传的音频
        response = websocket.receive_json()
        assert response["type"] == "audio"

        # 验证音频数据
        received_audio = base64.b64decode(response["data"])
        assert received_audio == audio_data


def test_websocket_control():
    """测试控制消息"""
    with client.websocket_connect("/ws/test-session") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送控制消息
        message = {
            "type": "control",
            "action": "pause",
            "session_id": "test-session"
        }
        websocket.send_json(message)

        # 接收状态更新
        status = websocket.receive_json()
        assert status["type"] == "status"
        assert status["status"] == "idle"
```

---

## 五、性能指标

### 5.1 延迟预算

| 操作 | 目标延迟 | 实现方式 |
|------|---------|---------|
| WebSocket 连接建立 | < 50ms | FastAPI 原生支持 |
| 音频传输（单向） | < 10ms | 二进制帧，无编码 |
| JSON 消息解析 | < 5ms | Pydantic 验证 |
| 状态更新 | < 5ms | 内存操作 |
| **总计（基础通信）** | **< 70ms** | - |

### 5.2 并发处理

- **单会话**: 独立 asyncio 任务
- **多会话**: 每个会话独立协程
- **最大并发**: 100 个活跃会话（单进程）
- **扩展方式**: 多进程 + Redis 共享状态

---

## 六、下一步

阶段1完成后，继续：

- **阶段2**: VAD 语音检测模块（Silero VAD 集成）
- **阶段3**: TTS 流式合成模块（Edge TTS 集成）
- **阶段4**: LLM 流式生成模块（Claude API 集成）
- **阶段5**: 状态管理 + 导演指令模块
- **阶段6**: 集成测试 + 性能优化

---

## 七、快速启动

```bash
# 1. 创建目录结构
cd O:\AII\app\references
mkdir -p src/websocket src/models src/utils tests docs/api

# 2. 创建 __init__.py 文件
touch src/__init__.py
touch src/websocket/__init__.py
touch src/models/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

# 3. 运行服务
python3 src/server.py

# 4. 运行测试
pytest tests/ -v
```

---

**文档版本**: v1.0
**最后更新**: 2026-04-25
**作者**: Claude Sonnet 4.6
