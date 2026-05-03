"""
SQLAlchemy 持久化存储层 - 替代 JSON 文件存储

支持 SQLite（开发）/ PostgreSQL（生产）
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine, Column, String, Float, Integer, Text, DateTime,
    ForeignKey, JSON, Index, Boolean, select, delete, desc, func
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.pool import StaticPool

from src.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


# ── ORM Models ────────────────────────────────────────────────

class ConversationTurn(Base):
    """对话轮次"""
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), nullable=False)        # user / assistant
    content = Column(Text, nullable=False)
    timestamp = Column(Float, default=lambda: datetime.now().timestamp())

    __table_args__ = (
        Index("idx_turns_session_time", "session_id", "timestamp"),
    )


class LongTermMemory(Base):
    """长期记忆"""
    __tablename__ = "long_term_memories"

    id = Column(String(32), primary_key=True)         # MD5 hash of content
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)
    memory_type = Column(String(32), default="fact")   # fact / preference / identity / event
    metadata_json = Column("metadata", Text, default="{}")
    timestamp = Column(Float, default=lambda: datetime.now().timestamp())
    access_count = Column(Integer, default=0)
    last_access = Column(Float, default=lambda: datetime.now().timestamp())
    character = Column(String(64), default="default", index=True)

    @property
    def metadata_dict(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

    __table_args__ = (
        Index("idx_memories_type_char", "memory_type", "character"),
    )


class MemoryEmbedding(Base):
    """长期记忆向量（与 LongTermMemory 1:1）"""
    __tablename__ = "memory_embeddings"

    memory_id = Column(String(32), ForeignKey("long_term_memories.id", ondelete="CASCADE"), primary_key=True)
    vector_blob = Column(Text, nullable=False)          # JSON-encoded float list
    dim = Column(Integer, default=1536)

    @property
    def vector(self) -> List[float]:
        return json.loads(self.vector_blob)

    @vector.setter
    def vector(self, v: List[float]):
        self.vector_blob = json.dumps(v)


class CharacterCard(Base):
    """角色卡片"""
    __tablename__ = "character_cards"

    name = Column(String(64), primary_key=True)
    description = Column(Text, default="")
    personality = Column(Text, default="")
    scenario = Column(Text, default="")
    first_mes = Column(Text, default="")
    mes_example = Column(Text, default="")
    system_prompt = Column(Text, default="")
    creator = Column(String(64), default="System")
    tags_json = Column("tags", Text, default="[]")
    custom_fields_json = Column("custom_fields", Text, default="{}")
    created_at = Column(Float, default=lambda: datetime.now().timestamp())
    updated_at = Column(Float, default=lambda: datetime.now().timestamp())

    @property
    def tags(self) -> List[str]:
        return json.loads(self.tags_json) if self.tags_json else []

    @tags.setter
    def tags(self, v: List[str]):
        self.tags_json = json.dumps(v)

    @property
    def custom_fields(self) -> dict:
        return json.loads(self.custom_fields_json) if self.custom_fields_json else {}

    @custom_fields.setter
    def custom_fields(self, v: dict):
        self.custom_fields_json = json.dumps(v)


class UserPreference(Base):
    """用户偏好（核心记忆 - 永不过期）"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(128), nullable=False, unique=True)
    value = Column(Text, default="")
    category = Column(String(32), default="general")   # general / voice / interaction / identity
    timestamp = Column(Float, default=lambda: datetime.now().timestamp())


# ── Database Manager ──────────────────────────────────────────

class DatabaseManager:
    """统一数据库管理器"""

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.environ.get(
                "DATABASE_URL",
                "sqlite:///data/voices.db"
            )
        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
            poolclass=StaticPool if "sqlite" in db_url else None,
            echo=False,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    @classmethod
    def get_instance(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def close(self):
        self.engine.dispose()


# ── Repository: Conversation ──────────────────────────────────

class ConversationRepository:
    """对话历史仓库"""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager.get_instance()

    def add_turn(self, session_id: str, role: str, content: str):
        with self.db.get_session() as s:
            s.add(ConversationTurn(session_id=session_id, role=role, content=content))
            s.commit()

    def get_recent_turns(self, session_id: str, limit: int = 30) -> List[Dict]:
        with self.db.get_session() as s:
            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.session_id == session_id)
                .order_by(desc(ConversationTurn.timestamp))
                .limit(limit)
            )
            rows = s.execute(stmt).scalars().all()
            return [
                {"role": r.role, "content": r.content, "timestamp": r.timestamp}
                for r in reversed(rows)
            ]

    def clear_session(self, session_id: str):
        with self.db.get_session() as s:
            s.execute(delete(ConversationTurn).where(ConversationTurn.session_id == session_id))
            s.commit()

    def count_sessions(self) -> int:
        with self.db.get_session() as s:
            return s.execute(
                select(func.count(func.distinct(ConversationTurn.session_id)))
            ).scalar()


# ── Repository: Long-Term Memory ───────────────────────────────

class MemoryRepository:
    """长期记忆仓库"""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager.get_instance()

    def upsert_memory(
        self, content: str, importance: float = 0.5,
        memory_type: str = "fact", character: str = "default",
        embedding: List[float] = None,
    ) -> str:
        import hashlib
        mem_id = hashlib.md5(content.encode()).hexdigest()

        with self.db.get_session() as s:
            existing = s.get(LongTermMemory, mem_id)
            if existing:
                existing.importance = max(existing.importance, importance)
                existing.access_count += 1
                existing.last_access = datetime.now().timestamp()
            else:
                s.add(LongTermMemory(
                    id=mem_id, content=content, importance=importance,
                    memory_type=memory_type, character=character,
                ))
                if embedding:
                    s.add(MemoryEmbedding(memory_id=mem_id, vector=embedding))
            s.commit()
        return mem_id

    def search_by_type(self, character: str, memory_type: str, limit: int = 10) -> List[Dict]:
        with self.db.get_session() as s:
            stmt = (
                select(LongTermMemory)
                .where(LongTermMemory.character == character)
                .where(LongTermMemory.memory_type == memory_type)
                .order_by(desc(LongTermMemory.importance))
                .limit(limit)
            )
            rows = s.execute(stmt).scalars().all()
            return [{"id": r.id, "content": r.content, "importance": r.importance} for r in rows]

    def evict_low_value(self, character: str, keep: int = 200):
        """移除低价值记忆"""
        with self.db.get_session() as s:
            stmt = (
                select(LongTermMemory)
                .where(LongTermMemory.character == character)
                .order_by(LongTermMemory.importance.asc(), LongTermMemory.last_access.asc())
            )
            rows = s.execute(stmt).scalars().all()
            to_delete = rows[:-keep] if len(rows) > keep else []
            for r in to_delete:
                s.delete(r)
            s.commit()
            if to_delete:
                logger.info(f"Evicted {len(to_delete)} low-value memories for {character}")


# ── Repository: Character Cards ───────────────────────────────

class CharacterRepository:
    """角色卡片仓库"""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager.get_instance()

    def create(self, name: str, **kwargs) -> CharacterCard:
        with self.db.get_session() as s:
            if s.get(CharacterCard, name):
                raise ValueError(f"Character '{name}' already exists")
            card = CharacterCard(name=name, **kwargs)
            s.add(card)
            s.commit()
            return card

    def get(self, name: str) -> Optional[CharacterCard]:
        with self.db.get_session() as s:
            return s.get(CharacterCard, name)

    def list_all(self) -> List[str]:
        with self.db.get_session() as s:
            return list(s.execute(
                select(CharacterCard.name).order_by(CharacterCard.updated_at.desc())
            ).scalars().all())

    def update(self, name: str, **kwargs) -> bool:
        with self.db.get_session() as s:
            card = s.get(CharacterCard, name)
            if not card:
                return False
            for k, v in kwargs.items():
                if hasattr(card, k):
                    setattr(card, k, v)
            card.updated_at = datetime.now().timestamp()
            s.commit()
            return True

    def delete(self, name: str) -> bool:
        with self.db.get_session() as s:
            card = s.get(CharacterCard, name)
            if not card:
                return False
            s.delete(card)
            s.commit()
            return True

    def search_by_tag(self, tag: str) -> List[str]:
        with self.db.get_session() as s:
            rows = s.execute(select(CharacterCard)).scalars().all()
            return [r.name for r in rows if tag in (r.tags or [])]

    def count(self) -> int:
        with self.db.get_session() as s:
            return s.execute(select(func.count(CharacterCard.name))).scalar()


# ── Repository: User Preferences ───────────────────────────────

class PreferenceRepository:
    """用户偏好仓库"""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager.get_instance()

    def set(self, key: str, value: str, category: str = "general"):
        with self.db.get_session() as s:
            pref = s.execute(
                select(UserPreference).where(UserPreference.key == key)
            ).scalar_one_or_none()
            if pref:
                pref.value = value
                pref.category = category
            else:
                s.add(UserPreference(key=key, value=value, category=category))
            s.commit()

    def get(self, key: str) -> Optional[str]:
        with self.db.get_session() as s:
            stmt = select(UserPreference).where(UserPreference.key == key)
            pref = s.execute(stmt).scalar_one_or_none()
            return pref.value if pref else None

    def get_all(self, category: str = None) -> Dict[str, str]:
        with self.db.get_session() as s:
            stmt = select(UserPreference)
            if category:
                stmt = stmt.where(UserPreference.category == category)
            rows = s.execute(stmt).scalars().all()
            return {r.key: r.value for r in rows}

    def delete(self, key: str):
        with self.db.get_session() as s:
            s.execute(delete(UserPreference).where(UserPreference.key == key))
            s.commit()


# ── Init ───────────────────────────────────────────────────────

def init_database(db_url: str = None):
    """初始化数据库，创建所有表。在应用启动时调用。"""
    db = DatabaseManager(db_url)
    db.create_tables()
    logger.info("Database initialized")
    return db
