"""
WebSocket 连接管理器
"""
from fastapi import WebSocket
from typing import Dict, Optional
import asyncio
import json
from datetime import datetime
import base64

from src.models.session_state import SessionState
from src.models.messages import (
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
        # session_id -> audio_counter (用于生成独立音频文件)
        self.audio_counters: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """接受新连接"""
        await websocket.accept()

        self.active_connections[session_id] = websocket

        # 创建或恢复会话状态
        if session_id not in self.session_states:
            self.session_states[session_id] = SessionState(session_id=session_id)
            self.audio_counters[session_id] = 0  # 初始化音频计数器
        else:
            # 恢复会话，更新活动时间
            self.session_states[session_id].update_activity()

        print(f"[{datetime.now()}] Session {session_id} connected")

        # 发送连接成功消息
        await self.send_status(session_id, "listening")

    def disconnect(self, session_id: str):
        """断开连接并清理会话资源"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
        if session_id in self.audio_counters:
            del self.audio_counters[session_id]

        print(f"[{datetime.now()}] Session {session_id} disconnected")

    async def send_audio(self, session_id: str, audio_data: bytes, is_new_file: bool = False, format: str = "mp3", is_final: bool = False):
        """发送音频数据"""
        if session_id not in self.active_connections:
            return

        # 如果是新文件，增加计数器
        if is_new_file:
            self.audio_counters[session_id] += 1

        audio_index = self.audio_counters[session_id]

        message = AudioMessage(
            data=base64.b64encode(audio_data).decode('utf-8'),
            format=format,
            session_id=session_id,
            audio_index=audio_index,
            is_new_file=is_new_file,
            is_final=is_final
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

    async def send_json(self, session_id: str, data: dict):
        """发送 JSON 数据"""
        if session_id not in self.active_connections:
            return

        await self.active_connections[session_id].send_json(data)

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        return self.session_states.get(session_id)

    def is_connected(self, session_id: str) -> bool:
        """检查会话是否连接"""
        return session_id in self.active_connections
