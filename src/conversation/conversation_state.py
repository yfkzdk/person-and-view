"""
对话状态机 — 带快照和回滚的对话生命周期管理

功能：
- 状态追踪: IDLE → LISTENING → UNDERSTANDING → RESPONDING → SPEAKING
- 打断回滚: 保存稳定态快照，interrupt 时恢复
- 话题栈: 追踪当前话题，切换时清理旧上下文
- 上下文边界: 按语义完整度标记窗口位置
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import copy

logger = logging.getLogger(__name__)


class ConversationPhase(str, Enum):
    IDLE = "idle"               # Waiting for input
    LISTENING = "listening"     # Receiving user input (audio or text)
    UNDERSTANDING = "understanding"  # Processing emotion + memory
    RESPONDING = "responding"   # LLM generating text
    SPEAKING = "speaking"       # TTS playing audio


@dataclass
class ConversationSnapshot:
    """Capture of stable conversation state for rollback."""
    phase: ConversationPhase = ConversationPhase.IDLE
    # Context manager state (for rollback)
    history_length: int = 0          # Length of conversation_history in context_manager
    # Memory state
    short_term_length: int = 0       # Length of short_term conversation_history
    # Emotion state
    last_emotion_weights: Dict[str, float] = field(default_factory=lambda: {"neutral": 1.0})
    # Topic
    current_topic: Optional[str] = None
    topic_stack: List[str] = field(default_factory=list)
    # Timestamp
    captured_at: float = 0.0
    # User input that triggered this state (for recovery context)
    pending_input: Optional[str] = None


class TopicTracker:
    """Tracks conversation topics for context management."""

    MAX_TOPICS = 5

    def __init__(self):
        self.stack: List[str] = []      # Most recent topic last
        self.current: Optional[str] = None

    def detect_topic(self, user_input: str) -> Optional[str]:
        """Lightweight topic detection via keyword density."""
        # Simplified: uses message length and key terms as heuristics
        # Full implementation would use LLM topic extraction
        keywords = ["工作", "学习", "生活", "感情", "爱好", "技术", "游戏",
                   "音乐", "电影", "运动", "旅行", "美食", "健康", "家庭"]
        found = [kw for kw in keywords if kw in user_input]
        return found[0] if found else None

    def push(self, topic: str):
        """Push a new topic, evicting oldest if stack is full."""
        if topic == self.current:
            return
        if self.current:
            self.stack.append(self.current)
        self.current = topic
        if len(self.stack) > self.MAX_TOPICS:
            self.stack.pop(0)

    def pop(self) -> Optional[str]:
        """Return to previous topic."""
        if self.stack:
            self.current = self.stack.pop()
        return self.current

    def is_topic_switch(self, new_input: str) -> bool:
        """Check if input indicates a topic change."""
        detected = self.detect_topic(new_input)
        return detected is not None and detected != self.current


class ConversationStateMachine:
    """
    Conversation state machine with rollback support.

    Usage:
        sm = ConversationStateMachine()

        # On user input start
        sm.transition(ConversationPhase.LISTENING)

        # On interrupt during AI response
        sm.rollback()  # Restores to last IDLE snapshot

        # On response complete
        sm.transition(ConversationPhase.IDLE)
    """

    def __init__(self):
        self.phase = ConversationPhase.IDLE
        self.topic_tracker = TopicTracker()
        self._snapshot: Optional[ConversationSnapshot] = None
        self._last_stable_snapshot: Optional[ConversationSnapshot] = None
        self._transition_history: List[ConversationPhase] = []
        self._interrupted = False

        # External references set by dialogue_manager after init
        self.context_manager = None
        self.memory_system = None

    # ---- State transitions ----

    def transition(self, new_phase: ConversationPhase) -> None:
        """Transition to a new phase, capturing snapshot at stability points."""
        old_phase = self.phase
        self.phase = new_phase
        self._transition_history.append(new_phase)

        # Capture snapshot at stable states (for rollback)
        if new_phase in (ConversationPhase.IDLE, ConversationPhase.LISTENING):
            self._capture_snapshot(new_phase)

        # On entering RESPONDING, mark a semantic boundary for context
        if new_phase == ConversationPhase.RESPONDING:
            self._mark_context_boundary()

        logger.debug(f"State: {old_phase.value} → {new_phase.value}")

    def _capture_snapshot(self, phase: ConversationPhase):
        """Capture current state as rollback target."""
        snapshot = ConversationSnapshot(
            phase=phase,
            captured_at=datetime.now().timestamp(),
            current_topic=self.topic_tracker.current,
            topic_stack=list(self.topic_tracker.stack),
        )
        if self.context_manager:
            snapshot.history_length = len(self.context_manager.conversation_history)
        if self.memory_system:
            snapshot.short_term_length = len(self.memory_system.short_term.conversation_history)

        self._last_stable_snapshot = snapshot

    def _mark_context_boundary(self):
        """Mark the current position as a semantic boundary in context."""
        if self.context_manager and hasattr(self.context_manager, 'mark_boundary'):
            self.context_manager.mark_boundary()

    # ---- Rollback ----

    def rollback(self, pending_input: Optional[str] = None) -> ConversationSnapshot:
        """Rollback to last stable snapshot (IDLE or LISTENING). Called on interrupt."""
        self._interrupted = True

        if not self._last_stable_snapshot:
            logger.warning("No stable snapshot available for rollback")
            return ConversationSnapshot()

        snap = self._last_stable_snapshot
        self.phase = snap.phase

        # Restore topic
        self.topic_tracker.current = snap.current_topic
        self.topic_tracker.stack = list(snap.topic_stack)

        # Restore context_manager history (trim to snapshot length)
        if self.context_manager and snap.history_length > 0:
            history = self.context_manager.conversation_history
            if len(history) > snap.history_length:
                # Keep only messages up to the snapshot point
                self.context_manager.conversation_history = history[:snap.history_length]
                logger.info(
                    f"Rollback: trimmed history from {len(history)} → {snap.history_length} messages"
                )

        # Restore short_term memory
        if self.memory_system and snap.short_term_length > 0:
            st = self.memory_system.short_term.conversation_history
            if len(st) > snap.short_term_length:
                self.memory_system.short_term.conversation_history = st[:snap.short_term_length]
                logger.info(
                    f"Rollback: trimmed short-term from {len(st)} → {snap.short_term_length}"
                )

        if pending_input:
            snap.pending_input = pending_input

        logger.info(f"Rollback to {snap.phase.value} complete")
        return snap

    def is_interrupted(self) -> bool:
        return self._interrupted

    def clear_interrupt(self):
        self._interrupted = False

    # ---- Topic management ----

    def update_topic(self, user_input: str) -> bool:
        """Detect and track topic changes. Returns True if topic switched."""
        detected = self.topic_tracker.detect_topic(user_input)
        if detected and detected != self.topic_tracker.current:
            self.topic_tracker.push(detected)
            logger.info(f"Topic switch: → {detected}")
            return True
        return False

    def get_current_topic(self) -> Optional[str]:
        return self.topic_tracker.current

    # ---- Context trimming ----

    def trim_context_for_topic_switch(self):
        """
        When topic changes drastically, trim old context to avoid confusion.
        Keeps system prompt + last 3 messages.
        """
        if not self.context_manager:
            return
        history = self.context_manager.conversation_history
        if len(history) > 6:  # More than 3 turns
            self.context_manager.conversation_history = history[-6:]
            logger.info(f"Topic-switch trim: kept last 6 messages")

    # ---- Status for frontend ----

    def to_frontend_status(self) -> str:
        """Map internal phase to frontend status string."""
        mapping = {
            ConversationPhase.IDLE: "idle",
            ConversationPhase.LISTENING: "listening",
            ConversationPhase.UNDERSTANDING: "processing",
            ConversationPhase.RESPONDING: "processing",
            ConversationPhase.SPEAKING: "speaking",
        }
        return mapping.get(self.phase, "idle")
