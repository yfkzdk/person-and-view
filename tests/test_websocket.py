"""
WebSocket 测试
"""
import pytest
from fastapi.testclient import TestClient
from src.server import app
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

        # 发送音频数据（VAD 要求最小 512 samples = 1024 bytes for int16）
        # 生成 1024 字节的测试音频数据
        audio_data = b"\x00\x01" * 512  # 512 个 int16 samples
        websocket.send_bytes(audio_data)

        # 接收 VAD 状态消息
        response = websocket.receive_json()
        assert response["type"] == "vad_status"
        assert "is_speech" in response
        assert "timestamp" in response


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


def test_websocket_disconnect():
    """测试断开连接"""
    with client.websocket_connect("/ws/test-session") as websocket:
        # 接收初始状态
        websocket.receive_json()

        # 连接应该正常
        assert websocket is not None

    # 断开后应该清理资源
    # （这里只是验证没有异常）
