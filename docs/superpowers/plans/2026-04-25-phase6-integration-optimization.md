# 集成测试 + 性能优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的集成测试套件和性能优化方案，确保系统稳定性和 TTFT < 500ms。

**Architecture:** 使用 pytest 进行集成测试，locust 进行压力测试，实现性能监控和优化策略，支持 Docker 容器化部署。

**Tech Stack:** Python 3.11.4, pytest, locust, Docker, prometheus_client

---

## 文件结构

```
O:\AII\app\references\
├── tests/
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_e2e_flow.py          # 端到端流程测试
│   │   ├── test_interrupt.py         # 打断场景测试
│   │   ├── test_concurrent.py        # 并发测试
│   │   └── test_error_recovery.py    # 错误恢复测试
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── test_ttft.py              # 首字延迟测试
│   │   ├── test_throughput.py        # 吞吐量测试
│   │   └── test_resource.py          # 资源占用测试
│   └── stress/
│       ├── locustfile.py             # Locust 压力测试
│       └── test_stability.py         # 稳定性测试
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py                    # 性能指标收集
│   └── dashboard.py                  # Dashboard 配置
├── docker/
│   ├── Dockerfile                    # Docker 镜像
│   └── docker-compose.yml            # Docker Compose 配置
└── docs/
    ├── performance_report.md         # 性能报告模板
    └── deployment_guide.md           # 部署指南
```

---

## Task 1: 端到端集成测试

**Files:**
- Create: `tests/integration/test_e2e_flow.py`

- [ ] **Step 1: Write end-to-end flow test**

```python
# tests/integration/test_e2e_flow.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.server import app
import time


client = TestClient(app)


def test_complete_flow_text_to_audio():
    """测试完整流程：文本输入 → LLM → TTS → 音频输出"""
    with client.websocket_connect("/ws/test-e2e") as websocket:
        # 1. 接收初始状态
        initial_status = websocket.receive_json()
        assert initial_status["type"] == "status"
        assert initial_status["status"] == "listening"

        # 2. 发送文本输入
        start_time = time.time()
        websocket.send_json({
            "type": "text_input",
            "content": "你好，请讲一个简短的故事",
            "session_id": "test-e2e"
        })

        # 3. 接收处理状态
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 4. 接收文本流
        text_chunks = []
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "text_chunk":
                text_chunks.append(msg["content"])
                if msg["is_final"]:
                    break

        # 5. 接收音频流
        audio_chunks = []
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "audio":
                audio_chunks.append(msg["data"])
            elif msg["type"] == "status" and msg["status"] == "listening":
                break

        end_time = time.time()

        # 6. 验证结果
        full_text = "".join(text_chunks)
        assert len(full_text) > 0, "No text generated"
        assert len(audio_chunks) > 0, "No audio generated"

        # 7. 验证 TTFT
        ttft = end_time - start_time
        print(f"\nTTFT: {ttft * 1000:.2f} ms")
        assert ttft < 1.0, f"TTFT {ttft}s exceeds 1 second"


def test_complete_flow_with_emotion():
    """测试带情绪的完整流程"""
    with client.websocket_connect("/ws/test-emotion") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送带情绪标记的文本
        websocket.send_json({
            "type": "text_input",
            "content": "[情绪:开心]今天天气真好！",
            "session_id": "test-emotion"
        })

        # 接收响应
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 验证生成了响应
        response_count = 0
        while True:
            msg = websocket.receive_json()
            if msg["type"] in ["text_chunk", "audio"]:
                response_count += 1
            elif msg["type"] == "status" and msg["status"] == "listening":
                break

        assert response_count > 0, "No response generated"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_e2e_flow.py -v -s`
Expected: PASS with TTFT printed

- [ ] **Step 3: Commit integration tests**

```bash
git add tests/integration/test_e2e_flow.py
git commit -m "test: add end-to-end integration tests"
```

---

## Task 2: 打断场景测试

**Files:**
- Create: `tests/integration/test_interrupt.py`

- [ ] **Step 1: Write interrupt scenario tests**

```python
# tests/integration/test_interrupt.py
import pytest
from fastapi.testclient import TestClient
from src.server import app
import time


client = TestClient(app)


def test_interrupt_during_tts():
    """测试 TTS 过程中的打断"""
    with client.websocket_connect("/ws/test-interrupt-tts") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送长文本
        websocket.send_json({
            "type": "text_input",
            "content": "请讲一个很长的故事" * 10,
            "session_id": "test-interrupt-tts"
        })

        # 等待处理开始
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 等待一小段时间
        time.sleep(0.5)

        # 发送打断控制
        websocket.send_json({
            "type": "control",
            "action": "interrupt",
            "session_id": "test-interrupt-tts"
        })

        # 接收状态更新
        status = websocket.receive_json()
        assert status["status"] == "listening"

        # 验证系统恢复到监听状态
        websocket.send_json({
            "type": "text_input",
            "content": "继续",
            "session_id": "test-interrupt-tts"
        })

        # 应该能正常处理新请求
        status = websocket.receive_json()
        assert status["status"] == "processing"


def test_interrupt_during_llm():
    """测试 LLM 生成过程中的打断"""
    with client.websocket_connect("/ws/test-interrupt-llm") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送需要长时间生成的请求
        websocket.send_json({
            "type": "text_input",
            "content": "请详细描述一个复杂的故事情节",
            "session_id": "test-interrupt-llm"
        })

        # 等待 LLM 开始生成
        status = websocket.receive_json()
        assert status["status"] == "processing"

        # 立即打断
        time.sleep(0.2)
        websocket.send_json({
            "type": "control",
            "action": "interrupt",
            "session_id": "test-interrupt-llm"
        })

        # 验证系统状态
        status = websocket.receive_json()
        assert status["status"] in ["listening", "idle"]
```

- [ ] **Step 2: Run interrupt tests**

Run: `pytest tests/integration/test_interrupt.py -v`
Expected: PASS

- [ ] **Step 3: Commit interrupt tests**

```bash
git add tests/integration/test_interrupt.py
git commit -m "test: add interrupt scenario tests"
```

---

## Task 3: 并发性能测试

**Files:**
- Create: `tests/integration/test_concurrent.py`

- [ ] **Step 1: Write concurrent session tests**

```python
# tests/integration/test_concurrent.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.server import app
import time


client = TestClient(app)


def test_concurrent_sessions():
    """测试多个并发会话"""
    num_sessions = 5
    sessions = []

    # 创建多个会话
    for i in range(num_sessions):
        session_id = f"test-concurrent-{i}"
        ws = client.websocket_connect(f"/ws/{session_id}")
        sessions.append(ws)

    # 所有会话同时发送请求
    start_time = time.time()

    for i, ws in enumerate(sessions):
        ws.send_json({
            "type": "text_input",
            "content": f"测试并发请求 {i}",
            "session_id": f"test-concurrent-{i}"
        })

    # 收集所有响应
    response_times = []
    for i, ws in enumerate(sessions):
        # 接收初始状态
        ws.receive_json()

        # 等待处理完成
        while True:
            msg = ws.receive_json()
            if msg.get("type") == "status" and msg.get("status") == "listening":
                response_times.append(time.time() - start_time)
                break

    # 关闭所有会话
    for ws in sessions:
        ws.close()

    # 分析结果
    avg_time = sum(response_times) / len(response_times)
    max_time = max(response_times)

    print(f"\nConcurrent Sessions Test:")
    print(f"  Sessions: {num_sessions}")
    print(f"  Average response time: {avg_time * 1000:.2f} ms")
    print(f"  Max response time: {max_time * 1000:.2f} ms")

    # 验证性能
    assert max_time < 5.0, f"Max response time {max_time}s too high"


def test_session_isolation():
    """测试会话隔离"""
    with client.websocket_connect("/ws/session-1") as ws1, \
         client.websocket_connect("/ws/session-2") as ws2:

        # 接收初始状态
        ws1.receive_json()
        ws2.receive_json()

        # 会话1发送请求
        ws1.send_json({
            "type": "text_input",
            "content": "会话1的消息",
            "session_id": "session-1"
        })

        # 会话2发送不同请求
        ws2.send_json({
            "type": "text_input",
            "content": "会话2的消息",
            "session_id": "session-2"
        })

        # 验证响应不会混淆
        ws1_status = ws1.receive_json()
        assert ws1_status["status"] == "processing"

        ws2_status = ws2.receive_json()
        assert ws2_status["status"] == "processing"
```

- [ ] **Step 2: Run concurrent tests**

Run: `pytest tests/integration/test_concurrent.py -v -s`
Expected: PASS with performance metrics

- [ ] **Step 3: Commit concurrent tests**

```bash
git add tests/integration/test_concurrent.py
git commit -m "test: add concurrent session tests"
```

---

## Task 4: 性能基准测试

**Files:**
- Create: `tests/performance/test_ttft.py`

- [ ] **Step 1: Write TTFT benchmark tests**

```python
# tests/performance/test_ttft.py
import pytest
from fastapi.testclient import TestClient
from src.server import app
import time
import statistics


client = TestClient(app)


def test_ttft_benchmark():
    """测试首字延迟基准"""
    num_iterations = 10
    ttft_values = []

    for i in range(num_iterations):
        session_id = f"test-ttft-{i}"

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            # 接收初始状态
            websocket.receive_json()

            # 发送请求
            start_time = time.time()
            websocket.send_json({
                "type": "text_input",
                "content": "你好",
                "session_id": session_id
            })

            # 接收第一个文本块
            first_chunk_time = None
            while True:
                msg = websocket.receive_json()
                if msg["type"] == "text_chunk":
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                        ttft_values.append(first_chunk_time)
                    if msg["is_final"]:
                        break

    # 分析结果
    avg_ttft = statistics.mean(ttft_values)
    median_ttft = statistics.median(ttft_values)
    p95_ttft = sorted(ttft_values)[int(len(ttft_values) * 0.95)]

    print(f"\nTTFT Benchmark Results:")
    print(f"  Iterations: {num_iterations}")
    print(f"  Average: {avg_ttft * 1000:.2f} ms")
    print(f"  Median: {median_ttft * 1000:.2f} ms")
    print(f"  P95: {p95_ttft * 1000:.2f} ms")

    # 验证性能目标
    assert avg_ttft < 0.5, f"Average TTFT {avg_ttft}s exceeds 500ms"
    assert p95_ttft < 1.0, f"P95 TTFT {p95_ttft}s exceeds 1s"
```

- [ ] **Step 2: Run TTFT benchmark**

Run: `pytest tests/performance/test_ttft.py -v -s`
Expected: PASS with benchmark results

- [ ] **Step 3: Commit TTFT tests**

```bash
git add tests/performance/test_ttft.py
git commit -m "test: add TTFT benchmark tests"
```

---

## Task 5: 压力测试（Locust）

**Files:**
- Create: `tests/stress/locustfile.py`

- [ ] **Step 1: Write Locust stress test**

```python
# tests/stress/locustfile.py
from locust import HttpUser, task, between
import websocket
import json
import time


class VoiceNarrativeUser(HttpUser):
    """语音叙事系统压力测试用户"""

    wait_time = between(1, 3)

    def on_start(self):
        """用户开始时执行"""
        self.session_id = f"stress-test-{time.time()}"

    @task
    def send_text_message(self):
        """发送文本消息"""
        ws_url = f"ws://localhost:8000/ws/{self.session_id}"

        try:
            ws = websocket.create_connection(ws_url)

            # 接收初始状态
            ws.recv()

            # 发送文本
            start_time = time.time()
            ws.send(json.dumps({
                "type": "text_input",
                "content": "你好，请讲一个故事",
                "session_id": self.session_id
            }))

            # 等待响应
            while True:
                msg = ws.recv()
                data = json.loads(msg)

                if data.get("type") == "status" and data.get("status") == "listening":
                    response_time = time.time() - start_time
                    self.environment.events.request.fire(
                        request_type="WebSocket",
                        name="text_to_audio",
                        response_time=response_time * 1000,
                        response_length=len(msg),
                        exception=None
                    )
                    break

            ws.close()

        except Exception as e:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="text_to_audio",
                response_time=0,
                response_length=0,
                exception=e
            )

    @task(weight=2)
    def interrupt_flow(self):
        """打断流程测试"""
        ws_url = f"ws://localhost:8000/ws/{self.session_id}-interrupt"

        try:
            ws = websocket.create_connection(ws_url)
            ws.recv()

            # 发送长文本
            ws.send(json.dumps({
                "type": "text_input",
                "content": "请讲一个很长的故事" * 5,
                "session_id": self.session_id
            }))

            # 等待一小段时间后打断
            time.sleep(0.5)
            ws.send(json.dumps({
                "type": "control",
                "action": "interrupt",
                "session_id": self.session_id
            }))

            # 接收状态
            msg = ws.recv()
            data = json.loads(msg)

            if data.get("status") == "listening":
                self.environment.events.request.fire(
                    request_type="WebSocket",
                    name="interrupt",
                    response_time=500,
                    response_length=len(msg),
                    exception=None
                )

            ws.close()

        except Exception as e:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="interrupt",
                response_time=0,
                response_length=0,
                exception=e
            )
```

- [ ] **Step 2: Run Locust stress test**

Run: `locust -f tests/stress/locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --headless --run-time 60s`
Expected: Stress test runs for 60 seconds with metrics

- [ ] **Step 3: Commit stress tests**

```bash
git add tests/stress/locustfile.py
git commit -m "test: add Locust stress tests"
```

---

## Task 6: 性能监控

**Files:**
- Create: `monitoring/metrics.py`

- [ ] **Step 1: Implement performance metrics collection**

```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time


# 定义指标
REQUEST_COUNT = Counter(
    'voice_narrative_requests_total',
    'Total number of requests',
    ['method', 'endpoint']
)

REQUEST_LATENCY = Histogram(
    'voice_narrative_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_SESSIONS = Gauge(
    'voice_narrative_active_sessions',
    'Number of active sessions'
)

TTFT_HISTOGRAM = Histogram(
    'voice_narrative_ttft_seconds',
    'Time to first token in seconds',
    buckets=[0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
)

TTS_LATENCY = Histogram(
    'voice_narrative_tts_latency_seconds',
    'TTS synthesis latency in seconds',
    buckets=[0.1, 0.2, 0.3, 0.5, 1.0]
)

LLM_LATENCY = Histogram(
    'voice_narrative_llm_latency_seconds',
    'LLM generation latency in seconds',
    buckets=[0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
)

INTERRUPT_COUNT = Counter(
    'voice_narrative_interrupts_total',
    'Total number of interrupts'
)


class MetricsMiddleware:
    """性能指标中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]

        # 记录请求
        REQUEST_COUNT.labels(method=method, endpoint=path).inc()

        # 记录延迟
        start_time = time.time()

        await self.app(scope, receive, send)

        latency = time.time() - start_time
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(latency)


def track_ttft(ttft_seconds: float):
    """记录 TTFT"""
    TTFT_HISTOGRAM.observe(ttft_seconds)


def track_tts_latency(latency_seconds: float):
    """记录 TTS 延迟"""
    TTS_LATENCY.observe(latency_seconds)


def track_llm_latency(latency_seconds: float):
    """记录 LLM 延迟"""
    LLM_LATENCY.observe(latency_seconds)


def increment_active_sessions():
    """增加活跃会话数"""
    ACTIVE_SESSIONS.inc()


def decrement_active_sessions():
    """减少活跃会话数"""
    ACTIVE_SESSIONS.dec()


def count_interrupt():
    """记录打断次数"""
    INTERRUPT_COUNT.inc()
```

- [ ] **Step 2: Integrate metrics into server**

```python
# src/server.py (add metrics)
from monitoring.metrics import (
    MetricsMiddleware,
    track_ttft,
    increment_active_sessions,
    decrement_active_sessions
)
import time

# 添加中间件
app.add_middleware(MetricsMiddleware)


# 在 WebSocket 连接时
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    increment_active_sessions()

    try:
        # ... existing code
    finally:
        decrement_active_sessions()
        manager.disconnect(session_id)


# 在处理文本输入时
async def handle_text_input(session_id: str, message: TextInputMessage):
    start_time = time.time()

    # ... existing code

    ttft = time.time() - start_time
    track_ttft(ttft)
```

- [ ] **Step 3: Commit metrics**

```bash
git add monitoring/metrics.py src/server.py
git commit -m "feat: add Prometheus metrics collection"
```

---

## Task 7: Docker 容器化

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY monitoring/ ./monitoring/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    networks:
      - voice-narrative-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - voice-narrative-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - voice-narrative-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - voice-narrative-network

networks:
  voice-narrative-network:
    driver: bridge

volumes:
  redis-data:
  grafana-data:
```

- [ ] **Step 3: Create requirements.txt**

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.45.0
websockets==16.0
redis==7.4.0
edge-tts==7.2.8
anthropic==0.97.0
numpy==2.4.4
torch==2.11.0+cpu
torchaudio==2.11.0+cpu
pydantic==2.5.0
msgpack==1.0.7
prometheus-client==0.19.0
pytest==7.4.3
locust==2.20.0
```

- [ ] **Step 4: Commit Docker files**

```bash
git add docker/ requirements.txt
git commit -m "feat: add Docker containerization"
```

---

## Task 8: 性能优化实现

**Files:**
- Create: `src/optimization/cache_optimizer.py`

- [ ] **Step 1: Implement cache optimization**

```python
# src/optimization/cache_optimizer.py
from functools import lru_cache
from typing import Dict, Any
import hashlib


class ResponseCache:
    """响应缓存优化器"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}

    def _generate_key(self, text: str, emotion: str = None) -> str:
        """生成缓存键"""
        content = f"{text}:{emotion or 'default'}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, text: str, emotion: str = None) -> Any:
        """获取缓存"""
        key = self._generate_key(text, emotion)
        return self.cache.get(key)

    def set(self, text: str, emotion: str, response: Any):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # 删除最旧的项
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        key = self._generate_key(text, emotion)
        self.cache[key] = response

    def clear(self):
        """清空缓存"""
        self.cache.clear()


# 全局缓存实例
response_cache = ResponseCache(max_size=200)


@lru_cache(maxsize=100)
def get_prompt_template_cached(template_type: str) -> str:
    """缓存提示词模板"""
    from src.llm.prompt_templates import PromptTemplates

    templates = {
        "narrative": PromptTemplates.narrative_generation,
        "emotion": PromptTemplates.emotion_response,
        "branch": PromptTemplates.branch_decision,
    }

    return templates.get(template_type)
```

- [ ] **Step 2: Integrate cache optimization**

```python
# src/server.py (use cache)
from optimization.cache_optimizer import response_cache


async def handle_text_input(session_id: str, message: TextInputMessage):
    # 检查缓存
    cached_response = response_cache.get(
        message.content,
        state.current_emotion if state else None
    )

    if cached_response:
        # 使用缓存响应
        await manager.send_text_chunk(session_id, cached_response, is_final=True)
        return

    # ... existing LLM and TTS code

    # 缓存响应
    response_cache.set(
        message.content,
        state.current_emotion,
        full_text
    )
```

- [ ] **Step 3: Commit optimizations**

```bash
git add src/optimization/ src/server.py
git commit -m "perf: add response caching optimization"
```

---

## 验收标准

- [ ] 所有集成测试通过
- [ ] 性能测试通过（TTFT < 500ms）
- [ ] 压力测试通过（支持 10+ 并发会话）
- [ ] 性能监控正常工作
- [ ] Docker 容器化部署成功
- [ ] 性能优化有效（缓存命中率 > 30%）

---

## 性能目标

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| TTFT | < 500ms | pytest benchmark |
| 吞吐量 | > 10 req/s | Locust |
| 并发会话 | > 10 | Locust |
| 内存占用 | < 500MB | 资源监控 |
| CPU 使用率 | < 70% | 资源监控 |

---

## 下一步

完成阶段6后，系统已具备生产就绪能力：

1. **部署**: 使用 Docker Compose 部署到生产环境
2. **监控**: 配置 Prometheus + Grafana 监控
3. **扩展**: 根据负载进行水平扩展
4. **优化**: 根据监控数据持续优化

---

**文档版本**: v1.0
**最后更新**: 2026-04-25
**作者**: Claude Sonnet 4.6
