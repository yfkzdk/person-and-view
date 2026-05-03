"""
智能记忆系统 — 语义向量检索 + 三层记忆生命周期

参考项目：Smart-Memory (https://github.com/senjinthedragon/Smart-Memory)
功能：
- 短期记忆（当前对话，30轮窗口）
- 长期记忆（语义向量检索，自动遗忘）
- 核心记忆（固定10条，永不过期）
- 情节记忆（故事线追踪）
- LLM自动事实提取（替代正则）
- jieba关键词fallback
"""
from typing import List, Dict, Optional, Tuple, Callable, Awaitable
from pydantic import BaseModel, Field
from datetime import datetime
import json
import hashlib
import logging
import os
import re
from collections import defaultdict
import numpy as np

import jieba

from src.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Lightweight in-memory vector store with cosine similarity search."""

    def __init__(self, dim: int = 1536, max_items: int = 500):
        self.dim = dim
        self.max_items = max_items
        self._ids: List[str] = []
        self._vectors = np.empty((0, dim), dtype=np.float32)
        self._texts: Dict[str, str] = {}

    def add(self, item_id: str, vector: List[float], text: str = ""):
        if item_id in self._texts:
            return
        vec = np.array(vector, dtype=np.float32).reshape(1, -1)
        if self._vectors.shape[0] > 0:
            self._vectors = np.vstack([self._vectors, vec])
        else:
            self._vectors = vec
        self._ids.append(item_id)
        self._texts[item_id] = text
        # Evict oldest if over capacity
        while len(self._ids) > self.max_items:
            old_id = self._ids.pop(0)
            self._vectors = np.delete(self._vectors, 0, axis=0)
            self._texts.pop(old_id, None)

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """Cosine similarity search. Returns [(id, score), ...]."""
        if self._vectors.shape[0] == 0:
            return []
        query = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm < 1e-8:
            return [(self._ids[i], 0.0) for i in range(min(top_k, len(self._ids)))]
        query = query / query_norm
        vec_norms = np.linalg.norm(self._vectors, axis=1)
        vec_norms = np.where(vec_norms < 1e-8, 1e-8, vec_norms)
        similarities = np.dot(self._vectors, query) / vec_norms
        # Get top-k indices
        k = min(top_k, len(self._ids))
        top_indices = np.argpartition(similarities, -k)[-k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
        return [(self._ids[i], float(similarities[i])) for i in top_indices]

    def remove(self, item_id: str):
        if item_id in self._texts:
            idx = self._ids.index(item_id)
            self._ids.pop(idx)
            self._vectors = np.delete(self._vectors, idx, axis=0)
            self._texts.pop(item_id, None)

    def __len__(self):
        return len(self._ids)


class MemoryItem(BaseModel):
    """记忆项"""
    content: str = Field(..., description="记忆内容")
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    importance: float = Field(0.5, ge=0.0, le=1.0, description="重要性 0-1")
    memory_type: str = Field("fact", description="记忆类型: fact/event/preference")
    metadata: Dict = Field(default_factory=dict, description="元数据")

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "memory_type": self.memory_type,
            "metadata": self.metadata
        }


class ShortTermMemory:
    """
    短期记忆 - 当前对话上下文

    特点：
    - 容量有限（最近N轮对话）
    - 自动遗忘旧对话
    - 快速访问
    """

    def __init__(self, max_turns: int = 10):
        """
        初始化短期记忆

        Args:
            max_turns: 最大对话轮数
        """
        self.max_turns = max_turns
        self.conversation_history: List[Dict] = []

    def add_message(self, role: str, content: str):
        """添加消息"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().timestamp()
        }

        self.conversation_history.append(message)

        # 超过容量，移除最旧的
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history.pop(0)

    def get_context(self, last_n: Optional[int] = None) -> List[Dict]:
        """
        获取对话上下文

        Args:
            last_n: 获取最近N轮，None表示全部

        Returns:
            对话历史
        """
        if last_n is None:
            return self.conversation_history
        return self.conversation_history[-last_n:]

    def clear(self):
        """清空短期记忆"""
        self.conversation_history.clear()


class LongTermMemory:
    """
    长期记忆 — 语义向量检索 + 关键词 fallback。

    特点:
    - 向量语义相似度搜索
    - 关键词索引 fallback
    - 按重要性 + 访问频率自动遗忘
    - 持久化存储
    """

    def __init__(self, storage_file: str = "memory/long_term.json", max_items: int = 200):
        self.storage_file = storage_file
        self.max_items = max_items
        self.memories: Dict[str, MemoryItem] = {}
        self.index: Dict[str, List[str]] = defaultdict(list)
        self.vector_store = VectorStore(max_items=max_items)
        self._access_counts: Dict[str, int] = defaultdict(int)
        self._last_access: Dict[str, float] = {}

        self._load()

    def set_embed_fn(self, fn: Callable[[str], Awaitable[List[float]]]):
        """Wire an async embedding function (e.g., DeepSeek embed API)."""
        self._embed_fn = fn

    async def _get_vector(self, text: str) -> Optional[List[float]]:
        if hasattr(self, '_embed_fn') and self._embed_fn:
            try:
                return await self._embed_fn(text)
            except Exception:
                return None
        return None

    async def add_memory(
        self,
        content: str,
        importance: float = 0.5,
        memory_type: str = "fact",
        metadata: Optional[Dict] = None,
        embedding: Optional[List[float]] = None
    ):
        memory_id = hashlib.md5(content.encode()).hexdigest()

        if memory_id in self.memories:
            # Update importance if existing
            self.memories[memory_id].importance = max(
                self.memories[memory_id].importance, importance
            )
            self._last_access[memory_id] = datetime.now().timestamp()
            self._access_counts[memory_id] += 1
            return

        memory = MemoryItem(
            content=content,
            importance=importance,
            memory_type=memory_type,
            metadata=metadata or {}
        )
        self.memories[memory_id] = memory

        # Keyword index (fallback)
        keywords = self._extract_keywords(content)
        for kw in keywords:
            self.index[kw].append(memory_id)

        # Vector index
        if embedding is None and hasattr(self, '_embed_fn') and self._embed_fn:
            embedding = await self._get_vector(content)
        if embedding:
            self.vector_store.add(memory_id, embedding, text=content[:200])

        # Evict if over capacity (by importance + last access)
        if len(self.memories) > self.max_items:
            self._evict_lowest()

        self._access_counts[memory_id] = 1
        self._last_access[memory_id] = datetime.now().timestamp()
        self._save()

    async def search(self, query: str, top_k: int = 3) -> List[MemoryItem]:
        """Semantic search with keyword fallback."""
        results = []

        # Try vector search first
        query_vec = await self._get_vector(query)
        if query_vec and len(self.vector_store) > 0:
            hits = self.vector_store.search(query_vec, top_k=top_k * 2)
            for mem_id, score in hits:
                if mem_id in self.memories:
                    mem = self.memories[mem_id]
                    # Boost by importance and recency
                    access_bonus = min(0.1, self._access_counts.get(mem_id, 0) * 0.01)
                    boosted = score * 0.7 + mem.importance * 0.2 + access_bonus
                    results.append((mem, boosted))
                    self._last_access[mem_id] = datetime.now().timestamp()
                    self._access_counts[mem_id] += 1

        # Keyword fallback (exact + substring)
        if len(results) < top_k:
            query_kw = self._extract_keywords(query)
            seen_ids = set()
            for kw in query_kw:
                matching_keys = {k for k in self.index if kw in k or k in kw}
                for key in matching_keys:
                    for mem_id in self.index[key]:
                        if mem_id not in seen_ids and mem_id in self.memories:
                            mem = self.memories[mem_id]
                            results.append((mem, mem.importance * 0.5))
                            seen_ids.add(mem_id)

        # Sort and deduplicate (by content hash)
        results.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        unique = []
        for mem, score in results:
            mem_id = hashlib.md5(mem.content.encode()).hexdigest()
            if mem_id not in seen:
                unique.append(mem)
                seen.add(mem_id)
        return unique[:top_k]

    def _evict_lowest(self):
        """Remove the least valuable memory (low importance + old access)."""
        if not self.memories:
            return
        now = datetime.now().timestamp()
        worst_id = None
        worst_score = float('inf')
        for mid, mem in self.memories.items():
            age_days = (now - self._last_access.get(mid, now)) / 86400
            score = mem.importance * 10 - age_days * 0.5
            if score < worst_score:
                worst_score = score
                worst_id = mid
        if worst_id:
            del self.memories[worst_id]
            self.vector_store.remove(worst_id)
            self._access_counts.pop(worst_id, None)
            self._last_access.pop(worst_id, None)
            # Clean keyword index
            for kw in list(self.index.keys()):
                self.index[kw] = [mid for mid in self.index[kw] if mid != worst_id]
            logger.info(f"Evicted memory: {worst_id[:16]}... (score={worst_score:.2f})")

    def _extract_keywords(self, text: str) -> List[str]:
        words = jieba.cut(text)
        stop_words = {"的","是","在","了","和","我","你","他","她","它",
                      "着","也","就","都","而","及","与","但","把","被",
                      "从","到","对","跟","给","让","叫","使","向","对",
                      "这","那","什么","怎么","哪","啊","吧","吗","呢","哦"}
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        data = {
            "memories": {mid: m.to_dict() for mid, m in self.memories.items()},
            "access_counts": dict(self._access_counts),
            "last_access": {k: v for k, v in self._last_access.items()}
        }
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(self.storage_file):
            return
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.memories = {
                mid: MemoryItem(**m)
                for mid, m in data.get("memories", {}).items()
            }
            self._access_counts = defaultdict(int, data.get("access_counts", {}))
            self._last_access = {k: float(v) for k, v in data.get("last_access", {}).items()}
            # Rebuild keyword index
            self.index = defaultdict(list)
            for mid, mem in self.memories.items():
                for kw in self._extract_keywords(mem.content):
                    self.index[kw].append(mid)
            # Trim if loaded data exceeds current max_items
            while len(self.memories) > self.max_items:
                self._evict_lowest()
        except (json.JSONDecodeError, OSError, Exception) as e:
            logger.warning(f"Failed to load memory from {self.storage_file}: {e}")


class EpisodicMemory:
    """
    情节记忆 - 故事线追踪

    特点：
    - 按时间顺序记录事件
    - 支持故事线提取
    - 自动摘要
    """

    def __init__(self):
        """初始化情节记忆"""
        self.episodes: List[Dict] = []

    def add_episode(
        self,
        event: str,
        participants: List[str] = None,
        location: str = None,
        timestamp: float = None
    ):
        """
        添加情节

        Args:
            event: 事件描述
            participants: 参与者
            location: 地点
            timestamp: 时间戳
        """
        episode = {
            "event": event,
            "participants": participants or [],
            "location": location,
            "timestamp": timestamp or datetime.now().timestamp()
        }

        self.episodes.append(episode)

    def get_storyline(self, last_n: int = None) -> List[Dict]:
        """
        获取故事线

        Args:
            last_n: 最近N个事件

        Returns:
            事件列表
        """
        if last_n is None:
            return self.episodes
        return self.episodes[-last_n:]

    def summarize(self, max_length: int = 200) -> str:
        """
        生成故事摘要

        Args:
            max_length: 最大长度

        Returns:
            摘要文本
        """
        if not self.episodes:
            return ""

        # 简单实现：拼接最近的事件
        recent_events = self.episodes[-5:]
        summary = " → ".join([ep["event"] for ep in recent_events])

        return summary[:max_length]


class CoreMemory:
    """
    核心记忆 — 固定容量，永不自动遗忘。

    存放用户最关键的信息：姓名、身份、长期偏好等。
    只有用户明确覆盖或手动删除才会更新。
    """

    MAX_ITEMS = 10

    def __init__(self):
        self.items: List[MemoryItem] = []

    def add(self, content: str, memory_type: str = "core"):
        # Deduplicate by content similarity (simple substring check)
        for item in self.items:
            if content in item.content or item.content in content:
                item.content = content  # Update
                item.timestamp = datetime.now().timestamp()
                return
        if len(self.items) >= self.MAX_ITEMS:
            # Replace oldest
            self.items.pop(0)
        self.items.append(MemoryItem(
            content=content,
            importance=1.0,
            memory_type=memory_type
        ))

    def to_context(self) -> str:
        if not self.items:
            return ""
        return "[核心信息]\n" + "\n".join(f"- {m.content}" for m in self.items)


class SmartMemorySystem:
    """
    智能记忆系统 — 三层记忆生命周期。

    短期记忆（30轮）→ 自动压缩 → 长期记忆（语义检索, 200条）→ 核心记忆（10条）
    """

    COMPRESS_TRIGGER_TURNS = 20
    COMPRESS_KEEP_RECENT = 10

    def __init__(
        self,
        max_short_term_turns: int = 30,
        storage_dir: str = "memory",
        auto_save: bool = True
    ):
        self.storage_dir = storage_dir
        self.auto_save = auto_save
        self.short_term = ShortTermMemory(max_turns=max_short_term_turns)
        self.long_term = LongTermMemory(
            storage_file=f"{storage_dir}/long_term.json",
            max_items=200
        )
        self.episodic = EpisodicMemory()
        self.core_memory = CoreMemory()

        self.relevance_threshold = 0.3
        self.conversation_summaries: List[str] = []
        self._summarize_fn = None  # Set by dialogue_manager for LLM summaries

    def set_embed_fn(self, fn: Callable[[str], Awaitable[List[float]]]):
        """Wire embedding function for semantic search."""
        self.long_term.set_embed_fn(fn)

    def set_summarize_fn(self, fn: Callable[[str], Awaitable[str]]):
        """Wire LLM summarize function for auto-compression."""
        self._summarize_fn = fn

    async def process_interaction(
        self,
        user_input: str,
        assistant_response: str
    ):
        # 1. Short-term
        self.short_term.add_message("user", user_input)
        self.short_term.add_message("assistant", assistant_response)

        # 2. LLM-based fact extraction (async, with regex fallback)
        await self._extract_important_info(user_input, assistant_response)

        # 3. Episodic
        self.episodic.add_episode(
            event=f"用户说：{user_input[:50]}... 助手回复：{assistant_response[:50]}..."
        )

        # 4. 自动保存到文件
        if self.auto_save:
            self.save_to_file()

    def save_to_file(self):
        """保存对话历史到JSON文件"""
        filepath = os.path.join(self.storage_dir, "history.json")
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            data = {
                "turns": self.short_term.conversation_history,
                "metadata": {
                    "last_saved": datetime.now().isoformat(),
                    "turn_count": len(self.short_term.conversation_history)
                }
            }
            content = json.dumps(data, ensure_ascii=False, indent=2)
            if len(content.encode('utf-8')) > settings.MEMORY_MAX_FILE_SIZE:
                # Truncate oldest turns to fit within size limit
                while len(content.encode('utf-8')) > settings.MEMORY_MAX_FILE_SIZE and data["turns"]:
                    data["turns"] = data["turns"][1:]
                    data["metadata"]["turn_count"] = len(data["turns"])
                    content = json.dumps(data, ensure_ascii=False, indent=2)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Failed to save conversation history to {filepath}: {e}")

    def load_from_file(self):
        """从JSON文件加载对话历史"""
        filepath = os.path.join(self.storage_dir, "history.json")
        if not os.path.exists(filepath):
            return  # First run, no history yet

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            turns = data.get("turns", [])
            if turns:
                self.short_term.conversation_history = turns
                logger.info(
                    f"Loaded {len(turns)} conversation turns from {filepath}"
                )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(
                f"Failed to load conversation history from {filepath}: {e}. "
                "Starting with empty history."
            )

    async def _extract_important_info(self, user_input: str, assistant_response: str):
        """
        Extract facts using LLM when available, falling back to regex patterns.
        Facts are stored in long-term memory with vector embeddings.
        """
        combined = f"用户: {user_input}\nAI: {assistant_response}"

        # Try LLM-based extraction first
        if self._summarize_fn:
            try:
                prompt = (
                    "从以下对话中提取用户的关键信息（偏好、事实、身份等），"
                    "以JSON数组返回，每项包含 content 和 type(preference/fact/identity):\n\n"
                    f"{combined}\n\n"
                    '输出格式: [{"content": "...", "type": "preference"}, ...]'
                    '如果没有值得记录的信息返回 []'
                )
                result = await self._summarize_fn(prompt)
                # Parse JSON from LLM response
                import re as _re
                json_match = _re.search(r'\[.*\]', result.replace('\n', ' '), _re.DOTALL)
                if json_match:
                    items = json.loads(json_match.group())
                    for item in items:
                        ct = item.get("content", "")
                        tp = item.get("type", "fact")
                        imp = 0.9 if tp == "preference" else 0.8
                        # Queue embedding in background
                        await self.long_term.add_memory(
                            content=ct,
                            importance=imp,
                            memory_type=tp
                        )
                    if items:
                        logger.info(f"LLM extracted {len(items)} facts")
                        return
            except Exception as e:
                logger.debug(f"LLM fact extraction failed, using regex fallback: {e}")

        # Regex fallback
        for pattern in ["我喜欢", "我讨厌", "我想要", "我希望"]:
            if pattern in user_input:
                await self.long_term.add_memory(content=user_input, importance=0.8, memory_type="preference")
                break

        for pattern in ["我是", "我叫", "我的", "我在", "我工作"]:
            if pattern in user_input:
                await self.long_term.add_memory(content=user_input, importance=0.7, memory_type="fact")
                break

    async def compress_history(self, summarize_fn) -> Optional[str]:
        """
        Compress oldest conversation turns into a summary when threshold exceeded.

        Args:
            summarize_fn: Async function (prompt: str) -> str that calls LLM

        Returns:
            Summary string if compression occurred, None otherwise
        """
        turns = self.short_term.conversation_history
        if len(turns) <= self.COMPRESS_TRIGGER_TURNS:
            return None

        # Take oldest turns to compress, keep most recent ones
        compress_count = len(turns) - self.COMPRESS_KEEP_RECENT
        turns_to_compress = turns[:compress_count]

        # Build summary prompt
        transcript = "\n".join(
            f"[{t['role']}]: {t['content'][:200]}" for t in turns_to_compress
        )
        prompt = (
            f"用2-3句中文总结以下对话的关键信息和用户偏好：\n\n{transcript}\n\n摘要："
        )

        try:
            summary = await summarize_fn(prompt)
            self.conversation_summaries.append(summary.strip())
            # Keep only recent turns in short-term memory
            self.short_term.conversation_history = turns[compress_count:]
            logger.info(
                f"Compressed {compress_count} turns into summary, "
                f"kept {len(self.short_term.conversation_history)} recent turns, "
                f"{len(self.conversation_summaries)} summaries total"
            )
            return summary.strip()
        except Exception as e:
            logger.warning(f"Failed to compress history: {e}")
            return None

    def get_conversation_compressed_context(self) -> str:
        """Get accumulated summaries as context string."""
        if not self.conversation_summaries:
            return ""
        parts = ["[对话历史摘要]"]
        for i, summary in enumerate(self.conversation_summaries, 1):
            parts.append(f"{i}. {summary}")
        return "\n".join(parts)

    async def get_relevant_context(self, current_input: str, max_chars: int = 600) -> str:
        """
        Get concise context for injection into the current turn.
        Context is transient — not persisted in conversation history.
        """
        context_parts = []

        # 0. Core memory (always injected, never expires)
        core = self.core_memory.to_context()
        if core:
            context_parts.append(core)

        # 1. Compressed summaries (last 2 only)
        if self.conversation_summaries:
            recent_summaries = self.conversation_summaries[-2:]
            parts = ["[对话摘要]"]
            for i, s in enumerate(recent_summaries, 1):
                parts.append(f"{i}. {s}")
            context_parts.append("\n".join(parts))

        # 1. Recent conversation (last 3 turns, truncated)
        recent = self.short_term.get_context(last_n=6)  # 3 user + 3 assistant
        if recent:
            lines = ["[最近对话]"]
            for msg in recent:
                role = "用户" if msg["role"] == "user" else "AI"
                snippet = msg["content"][:80].replace("\n", " ")
                lines.append(f"{role}: {snippet}")
            context_parts.append("\n".join(lines))

        # 2. Relevant long-term facts (top 2, truncated)
        relevant = await self.long_term.search(current_input, top_k=2)
        if relevant:
            lines = ["[相关记忆]"]
            for m in relevant:
                lines.append(f"- {m.content[:100]}")
            context_parts.append("\n".join(lines))

        # Assemble and cap
        full = "\n".join(context_parts)
        if len(full) > max_chars:
            # Truncate from the top (oldest info first)
            full = "…" + full[-(max_chars - 1):]
        return full

    def save_all(self):
        """保存所有记忆"""
        self.long_term._save()

    def clear_short_term(self):
        """清空短期记忆"""
        self.short_term.clear()


# 使用示例
if __name__ == "__main__":
    # 创建记忆系统
    memory = SmartMemorySystem()

    # 模拟对话
    memory.process_interaction(
        "你好，我是小明，我喜欢打篮球",
        "你好小明！很高兴认识你。打篮球是一项很棒的运动！"
    )

    memory.process_interaction(
        "我最近在学Python",
        "太好了！Python是一门非常实用的编程语言。有什么具体想学的吗？"
    )

    # 获取相关上下文
    context = memory.get_relevant_context("我想学编程")
    print("=" * 80)
    print("相关上下文：")
    print("=" * 80)
    print(context)

    # 保存记忆
    memory.save_all()
    print("\n✅ 记忆已保存")
