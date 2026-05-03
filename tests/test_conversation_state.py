"""
测试对话状态机 — 状态转换、快照回滚、话题追踪
"""
import pytest
from src.conversation.conversation_state import (
    ConversationStateMachine,
    ConversationPhase,
    ConversationSnapshot,
    TopicTracker,
)


class TestTopicTracker:
    def test_detect_known_topic(self):
        tt = TopicTracker()
        assert tt.detect_topic("我最近在学习") == "学习"
        assert tt.detect_topic("今天去运动了") == "运动"
        assert tt.detect_topic("没有关键词") is None

    def test_push_and_pop(self):
        tt = TopicTracker()
        tt.push("技术")
        assert tt.current == "技术"
        tt.push("生活")
        assert tt.current == "生活"
        assert tt.stack == ["技术"]
        popped = tt.pop()
        assert popped == "技术"
        assert tt.current == "技术"

    def test_stack_eviction(self):
        tt = TopicTracker()
        for t in ["a", "b", "c", "d", "e", "f", "g"]:
            tt.push(t)
        assert len(tt.stack) <= tt.MAX_TOPICS

    def test_topic_switch_detection(self):
        tt = TopicTracker()
        tt.push("技术")
        assert tt.is_topic_switch("我想去运动一下") is True
        assert tt.is_topic_switch("继续写代码") is False


class TestConversationStateMachine:
    def test_initial_state(self):
        sm = ConversationStateMachine()
        assert sm.phase == ConversationPhase.IDLE

    def test_transition_sequence(self):
        sm = ConversationStateMachine()
        sm.transition(ConversationPhase.LISTENING)
        assert sm.phase == ConversationPhase.LISTENING
        sm.transition(ConversationPhase.UNDERSTANDING)
        assert sm.phase == ConversationPhase.UNDERSTANDING
        sm.transition(ConversationPhase.RESPONDING)
        assert sm.phase == ConversationPhase.RESPONDING
        sm.transition(ConversationPhase.IDLE)
        assert sm.phase == ConversationPhase.IDLE

    def test_rollback_restores_phase(self):
        sm = ConversationStateMachine()
        # Start at IDLE, snapshot captured
        sm.transition(ConversationPhase.LISTENING)
        sm.transition(ConversationPhase.RESPONDING)
        # Interrupt!
        snap = sm.rollback()
        assert snap.phase == ConversationPhase.LISTENING
        assert sm.phase == ConversationPhase.LISTENING

    def test_rollback_with_context_manager(self):
        class MockContextManager:
            def __init__(self):
                self.conversation_history = list(range(20))  # 20 messages
        sm = ConversationStateMachine()
        sm.context_manager = MockContextManager()
        sm.transition(ConversationPhase.IDLE)
        # Simulate adding messages during RESPONDING
        sm.context_manager.conversation_history.extend([21, 22, 23])
        sm.rollback()
        # Should be trimmed back to snapshot length (20)
        assert len(sm.context_manager.conversation_history) == 20

    def test_mark_interrupted(self):
        sm = ConversationStateMachine()
        sm.transition(ConversationPhase.RESPONDING)
        sm.rollback()
        assert sm.is_interrupted() is True
        sm.clear_interrupt()
        assert sm.is_interrupted() is False

    def test_to_frontend_status(self):
        sm = ConversationStateMachine()
        assert sm.to_frontend_status() == "idle"
        sm.transition(ConversationPhase.RESPONDING)
        assert sm.to_frontend_status() == "processing"
        sm.transition(ConversationPhase.SPEAKING)
        assert sm.to_frontend_status() == "speaking"

    def test_topic_switch_trims_context(self):
        class MockCM:
            def __init__(self):
                self.conversation_history = list(range(10))
        sm = ConversationStateMachine()
        sm.context_manager = MockCM()
        sm.trim_context_for_topic_switch()
        assert len(sm.context_manager.conversation_history) == 6
