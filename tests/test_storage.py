"""
Database persistence tests
"""
import os
import pytest
from src.state.storage import (
    DatabaseManager, ConversationRepository,
    MemoryRepository, CharacterRepository, PreferenceRepository,
    init_database,
)


# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def db():
    """Create test database"""
    manager = DatabaseManager(TEST_DB_URL)
    manager.create_tables()
    yield manager
    manager.close()


class TestConversationRepository:
    def test_add_and_retrieve_turns(self, db):
        repo = ConversationRepository(db)
        repo.add_turn("session_1", "user", "Hello")
        repo.add_turn("session_1", "assistant", "Hi there!")

        turns = repo.get_recent_turns("session_1")
        assert len(turns) == 2
        assert turns[0]["role"] == "user"
        assert turns[1]["role"] == "assistant"

    def test_multiple_sessions(self, db):
        repo = ConversationRepository(db)
        repo.add_turn("s1", "user", "A")
        repo.add_turn("s2", "user", "B")
        assert repo.count_sessions() == 2

    def test_clear_session(self, db):
        repo = ConversationRepository(db)
        repo.add_turn("s1", "user", "Test")
        repo.clear_session("s1")
        assert len(repo.get_recent_turns("s1")) == 0


class TestMemoryRepository:
    def test_upsert_and_retrieve(self, db):
        repo = MemoryRepository(db)
        mid = repo.upsert_memory("I like basketball", importance=0.9, memory_type="preference", character="test")
        assert len(mid) == 32  # MD5 hash

        results = repo.search_by_type("test", "preference")
        assert len(results) >= 1
        assert "basketball" in results[0]["content"]

    def test_upsert_dedup_updates_importance(self, db):
        repo = MemoryRepository(db)
        repo.upsert_memory("I like hiking", importance=0.3, memory_type="fact", character="test")
        repo.upsert_memory("I like hiking", importance=0.9, memory_type="fact", character="test")
        results = repo.search_by_type("test", "fact")
        assert results[0]["importance"] >= 0.9

    def test_evict_low_value(self, db):
        repo = MemoryRepository(db)
        for i in range(5):
            repo.upsert_memory(f"Memory {i}", importance=0.1 * i, character="test")
        repo.evict_low_value("test", keep=3)
        results = repo.search_by_type("test", "fact", limit=10)
        assert len(results) <= 3


class TestCharacterRepository:
    def test_create_and_get(self, db):
        repo = CharacterRepository(db)
        repo.create("TestBot", description="A test character", personality="friendly", tags=["test"])
        card = repo.get("TestBot")
        assert card is not None
        assert card.description == "A test character"
        assert "test" in card.tags

    def test_create_duplicate_raises(self, db):
        repo = CharacterRepository(db)
        repo.create("UniqueBot")
        with pytest.raises(ValueError):
            repo.create("UniqueBot")

    def test_list_all(self, db):
        repo = CharacterRepository(db)
        repo.create("BotA")
        repo.create("BotB")
        assert set(repo.list_all()) == {"BotA", "BotB"}

    def test_update(self, db):
        repo = CharacterRepository(db)
        repo.create("Bot")
        repo.update("Bot", description="Updated")
        assert repo.get("Bot").description == "Updated"

    def test_delete(self, db):
        repo = CharacterRepository(db)
        repo.create("Bot")
        repo.delete("Bot")
        assert repo.get("Bot") is None

    def test_search_by_tag(self, db):
        repo = CharacterRepository(db)
        repo.create("Bot1", tags=["game", "fun"])
        repo.create("Bot2", tags=["work"])
        assert repo.search_by_tag("game") == ["Bot1"]

    def test_count(self, db):
        repo = CharacterRepository(db)
        repo.create("A")
        repo.create("B")
        assert repo.count() == 2


class TestPreferenceRepository:
    def test_set_and_get(self, db):
        repo = PreferenceRepository(db)
        repo.set("theme", "dark", category="ui")
        assert repo.get("theme") == "dark"

    def test_get_all_by_category(self, db):
        repo = PreferenceRepository(db)
        repo.set("k1", "v1", category="general")
        repo.set("k2", "v2", category="ui")
        general = repo.get_all("general")
        assert "k1" in general
        assert "k2" not in general

    def test_delete(self, db):
        repo = PreferenceRepository(db)
        repo.set("key", "value")
        repo.delete("key")
        assert repo.get("key") is None


class TestDatabaseInitialization:
    def test_init_creates_tables(self):
        db = init_database("sqlite:///:memory:")
        # Verify tables exist by running a query
        with db.get_session() as s:
            from sqlalchemy import text
            s.execute(text("SELECT 1 FROM character_cards LIMIT 0"))
            s.execute(text("SELECT 1 FROM conversation_turns LIMIT 0"))
            s.execute(text("SELECT 1 FROM long_term_memories LIMIT 0"))
        db.close()
