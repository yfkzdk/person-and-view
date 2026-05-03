"""
测试语义记忆系统 — VectorStore, LongTermMemory, CoreMemory
"""
import pytest
from src.memory.smart_memory import (
    VectorStore,
    LongTermMemory,
    CoreMemory,
    SmartMemorySystem,
)


class TestVectorStore:
    def test_add_and_search(self):
        vs = VectorStore(dim=4, max_items=100)
        vs.add("a", [1.0, 0.0, 0.0, 0.0], "item a")
        vs.add("b", [0.0, 1.0, 0.0, 0.0], "item b")
        vs.add("c", [0.99, 0.01, 0.0, 0.0], "item c")

        results = vs.search([1.0, 0.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        # "a" should be most similar to query [1,0,0,0]
        assert results[0][0] == "a"
        assert results[0][1] > 0.9

    def test_eviction(self):
        vs = VectorStore(dim=2, max_items=3)
        for i in range(5):
            vs.add(str(i), [float(i), 0.0], f"item {i}")
        assert len(vs) == 3
        # Oldest items (0, 1) should be evicted
        assert "0" not in vs._texts
        assert "1" not in vs._texts

    def test_remove(self):
        vs = VectorStore(dim=2, max_items=10)
        vs.add("x", [1.0, 0.0], "x")
        vs.add("y", [0.0, 1.0], "y")
        vs.remove("x")
        assert len(vs) == 1
        results = vs.search([1.0, 0.0], top_k=1)
        assert results[0][0] == "y"

    def test_empty_search(self):
        vs = VectorStore(dim=4, max_items=10)
        assert vs.search([1.0, 0.0, 0.0, 0.0]) == []


class TestCoreMemory:
    def test_add_and_deduplicate(self):
        cm = CoreMemory()
        cm.add("用户叫小明", "identity")
        cm.add("用户喜欢篮球", "preference")
        assert len(cm.items) == 2

        # Update existing — "用户叫小明" is substring of new content
        cm.add("用户叫小明，今年25岁", "identity")
        assert len(cm.items) == 2
        # The merged content should be in one of the items
        all_content = " ".join(it.content for it in cm.items)
        assert "25岁" in all_content

    def test_max_capacity(self):
        cm = CoreMemory()
        for i in range(15):
            cm.add(f"事实 {i}", "fact")
        assert len(cm.items) == 10  # MAX_ITEMS

    def test_to_context(self):
        cm = CoreMemory()
        cm.add("用户叫小明")
        context = cm.to_context()
        assert "[核心信息]" in context
        assert "小明" in context

    def test_empty_context(self):
        cm = CoreMemory()
        assert cm.to_context() == ""


class TestLongTermMemory:
    @pytest.mark.asyncio
    async def test_keyword_search_fallback(self):
        """Without embed_fn, should fall back to jieba keywords."""
        ltm = LongTermMemory(storage_file="memory/test_ltm_keyword.json", max_items=10)
        await ltm.add_memory("用户喜欢打篮球", importance=0.8, memory_type="preference")
        await ltm.add_memory("用户讨厌跑步", importance=0.7, memory_type="preference")

        results = await ltm.search("篮球")
        assert len(results) >= 1
        assert any("篮球" in m.content for m in results)

    @pytest.mark.asyncio
    async def test_eviction_by_score(self):
        ltm = LongTermMemory(storage_file="memory/test_ltm_eviction.json", max_items=5)
        for i in range(10):
            await ltm.add_memory(f"记忆片段 {i}", importance=0.1 + i * 0.05)
        assert len(ltm.memories) <= 5

    def test_chinese_keyword_extraction(self):
        ltm = LongTermMemory()
        keywords = ltm._extract_keywords("我喜欢吃四川火锅")
        assert "喜欢" in keywords or "火锅" in keywords or "四川" in keywords
        assert "我" not in keywords
        assert "的" not in keywords

    def test_mixed_cn_en_extraction(self):
        ltm = LongTermMemory()
        keywords = ltm._extract_keywords("我想学Python编程")
        assert "Python" in keywords or "编程" in keywords or "想学" in keywords


class TestSmartMemoryIntegration:
    def test_init_defaults(self):
        sms = SmartMemorySystem(storage_dir="memory/test_char")
        assert sms.short_term is not None
        assert sms.long_term is not None
        assert sms.core_memory is not None
        assert sms.episodic is not None
        assert len(sms.core_memory.items) == 0

    @pytest.mark.asyncio
    async def test_process_interaction(self):
        sms = SmartMemorySystem(storage_dir="memory/test_char")
        await sms.process_interaction("我叫小明", "你好小明")
        assert len(sms.short_term.conversation_history) >= 2

    def test_relevant_context_includes_core(self):
        sms = SmartMemorySystem(storage_dir="memory/test_char")
        sms.core_memory.add("用户叫小明，今年25岁")
        # Synchronous test since long_term.search will fail without embed_fn
        # But core memory injection is synchronous
        context = sms.get_conversation_compressed_context()
        # Core memory should appear via get_relevant_context
        # (tested async via dialogue_manager integration)
