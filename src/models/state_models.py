"""
状态模型
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class VectorClock(BaseModel):
    """向量时钟"""
    node_id: str = "edge"
    clock: Dict[str, int] = Field(default_factory=lambda: {"edge": 0})

    def increment(self):
        """递增本节点时钟"""
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def get_time(self, node_id: str) -> int:
        """获取指定节点的时间"""
        return self.clock.get(node_id, 0)

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """合并另一个向量时钟"""
        merged = VectorClock(node_id=self.node_id)

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
        clock = cls(node_id=node_id)
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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DirectorCommandState(BaseModel):
    """导演指令状态"""
    command: str
    value: Optional[float] = None
    applied: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)