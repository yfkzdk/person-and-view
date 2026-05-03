"""
性能基准测试
"""
import pytest
import time
import asyncio
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)


def test_ttft_performance():
    """测试首字延迟（TTFT）"""
    with client.websocket_connect("/ws/test-ttft") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送文本输入
        start = time.perf_counter()

        websocket.send_json({
            "type": "text_input",
            "content": "你好",
            "session_id": "test-ttft"
        })

        # 接收处理状态
        websocket.receive_json()

        # 接收第一个响应
        first_response = websocket.receive_json()
        ttft = time.perf_counter() - start

        print(f"\nTTFT: {ttft * 1000:.2f} ms")

        # 验证响应类型
        assert first_response["type"] in ["text_chunk", "audio", "status"]


def test_throughput_performance():
    """测试吞吐量"""
    with client.websocket_connect("/ws/test-throughput") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 发送多个请求
        num_requests = 10
        start = time.perf_counter()

        for i in range(num_requests):
            websocket.send_json({
                "type": "text_input",
                "content": f"测试消息 {i}",
                "session_id": "test-throughput"
            })

            # 接收响应
            responses = 0
            while responses < 5:  # 限制响应数量
                msg = websocket.receive_json()
                responses += 1

                if msg["type"] == "status" and msg["status"] == "listening":
                    break

        duration = time.perf_counter() - start
        throughput = num_requests / duration

        print(f"\nThroughput:")
        print(f"  Requests: {num_requests}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Requests/second: {throughput:.2f}")


def test_concurrent_sessions_performance():
    """测试并发会话性能"""
    num_sessions = 5
    sessions = []

    start = time.perf_counter()

    # 创建多个会话
    for i in range(num_sessions):
        ws = client.websocket_connect(f"/ws/test-concurrent-{i}")
        ws.receive_json()  # 接收初始状态
        sessions.append(ws)

    # 向每个会话发送消息
    for i, ws in enumerate(sessions):
        ws.send_json({
            "type": "text_input",
            "content": f"并发测试 {i}",
            "session_id": f"test-concurrent-{i}"
        })

    # 接收所有响应
    for ws in sessions:
        responses = 0
        while responses < 5:
            msg = ws.receive_json()
            responses += 1

            if msg["type"] == "status" and msg["status"] == "listening":
                break

    duration = time.perf_counter() - start

    print(f"\nConcurrent Sessions Performance:")
    print(f"  Sessions: {num_sessions}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Sessions/second: {num_sessions / duration:.2f}")

    # 关闭所有会话
    for ws in sessions:
        ws.close()


def test_message_latency():
    """测试消息延迟"""
    with client.websocket_connect("/ws/test-latency") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 测试多次消息延迟
        latencies = []

        for i in range(10):
            start = time.perf_counter()

            websocket.send_json({
                "type": "text_input",
                "content": f"延迟测试 {i}",
                "session_id": "test-latency"
            })

            # 接收处理状态
            websocket.receive_json()

            # 接收响应
            responses = 0
            while responses < 5:
                msg = websocket.receive_json()
                responses += 1

                if msg["type"] == "status" and msg["status"] == "listening":
                    break

            latency = time.perf_counter() - start
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        print(f"\nMessage Latency:")
        print(f"  Average: {avg_latency * 1000:.2f} ms")
        print(f"  Max: {max_latency * 1000:.2f} ms")
        print(f"  Min: {min_latency * 1000:.2f} ms")
