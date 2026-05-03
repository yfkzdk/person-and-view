"""
消息模型定义
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class AudioMessage(BaseModel):
    """音频数据消息"""
    type: Literal["audio"] = "audio"
    data: str  # base64-encoded
    format: str = "mp3"  # "mp3" or "wav"
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    session_id: Optional[str] = None
    audio_index: int = 0  # 音频文件序号
    is_new_file: bool = False  # 是否是新文件的第一个块
    is_final: bool = False  # 是否是最后一个音频块


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


class VADStatusMessage(BaseModel):
    """VAD 状态消息"""
    type: Literal["vad_status"] = "vad_status"
    is_speech: bool
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
