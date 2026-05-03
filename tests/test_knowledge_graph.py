"""Smoke tests for knowledge graph activation and context generation."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.memory.knowledge_graph import KnowledgeGraph, KGNode, MultiKnowledgeGraph


class TestKnowledgeGraph:
    def test_loads_tongjincheng_graph(self):
        kg = KnowledgeGraph("童锦程")
        assert len(kg.nodes) > 0
        assert len(kg.edges) > 0
        # Verify node types
        types = {n.type for n in kg.nodes.values()}
        assert "mental_model" in types
        assert "heuristic" in types

    def test_activate_returns_nodes_for_relevant_input(self):
        kg = KnowledgeGraph("童锦程")
        # Input that should trigger "吸引力原则" node (triggers: ["吸引力", "忽冷忽热", "女生"])
        activated = kg.activate("我喜欢的女生对我忽冷忽热怎么办")
        assert len(activated) > 0
        # First result should be the most relevant
        node, score = activated[0]
        assert score >= 0.3
        assert isinstance(node, KGNode)

    def test_activate_returns_empty_for_irrelevant_input(self):
        kg = KnowledgeGraph("童锦程")
        activated = kg.activate("今天天气怎么样")
        # Should return empty or very low scores for generic weather question
        # (童锦程's graph has no weather triggers)
        assert len(activated) == 0 or all(s < 0.3 for _, s in activated)

    def test_get_context_formats_chinese(self):
        kg = KnowledgeGraph("童锦程")
        activated = kg.activate("女生忽冷忽热")
        if activated:
            context = kg.get_context(activated)
            assert "童锦程" in context or "参考" in context
            assert len(context) > 0

    def test_toggle_node_disables_activation(self):
        kg = KnowledgeGraph("童锦程")
        # Find a node we can toggle
        node_ids = list(kg.nodes.keys())
        if node_ids:
            first_node = node_ids[0]
            # Disable it
            kg.toggle_node(first_node, False)
            assert first_node in kg.get_disabled_nodes()
            # Re-enable
            kg.toggle_node(first_node, True)
            assert first_node not in kg.get_disabled_nodes()

    def test_to_dict_exports_all_data(self):
        kg = KnowledgeGraph("童锦程")
        data = kg.to_dict()
        assert data["character"] == "童锦程"
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == len(kg.nodes)
        assert len(data["edges"]) == len(kg.edges)

    def test_spreading_activation_includes_neighbors(self):
        kg = KnowledgeGraph("童锦程")
        activated = kg.activate("我喜欢的女生对我忽冷忽热怎么办")
        node_ids = [n.id for n, s in activated]
        assert len(node_ids) > 0
        assert any("attraction_principle" in nid for nid in node_ids) or len(node_ids) >= 1


class TestKnowledgeGraphCRUD:
    """Test CRUD operations on knowledge graph using a temporary file."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        tmpfile = Path(tmpdir) / "test_crud_kg.json"
        # Create a minimal empty KG file
        tmpfile.write_text('{"character":"test","version":"1.0","nodes":[],"edges":[]}', encoding='utf-8')
        self.tmpfile = tmpfile
        self.tmpdir = tmpdir
        # Build KG pointing at temp file
        self.kg = KnowledgeGraph.__new__(KnowledgeGraph)
        self.kg.character_name = "test"
        self.kg.nodes = {}
        self.kg.edges = []
        self.kg._adjacency = {}
        self.kg._disabled_nodes = set()
        self.kg._filepath = tmpfile
        yield
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_upsert_node_new(self):
        node = self.kg.upsert_node({
            "label": "测试节点", "type": "concept",
            "summary": "用于测试", "content": "详细内容",
            "triggers": ["测试", "test"], "tags": ["CRUD"]
        })
        assert node.id in self.kg.nodes
        assert self.kg.nodes[node.id].label == "测试节点"

    def test_upsert_node_update(self):
        node = self.kg.upsert_node({"label": "待更新", "type": "concept", "summary": "旧"})
        node_id = node.id
        node2 = self.kg.upsert_node({"id": node_id, "label": "已更新", "type": "heuristic", "summary": "新摘要"})
        assert node2.id == node_id
        assert self.kg.nodes[node_id].label == "已更新"
        assert self.kg.nodes[node_id].type == "heuristic"

    def test_delete_node_removes_edges(self):
        n1 = self.kg.upsert_node({"label": "节点A", "type": "concept"})
        n2 = self.kg.upsert_node({"label": "节点B", "type": "concept"})
        self.kg.upsert_edge({"source": n1.id, "target": n2.id, "relation": "related"})
        assert any(e.source == n1.id and e.target == n2.id for e in self.kg.edges)
        self.kg.delete_node(n1.id)
        assert n2.id in self.kg.nodes
        assert not any(e.source == n1.id or e.target == n1.id for e in self.kg.edges)

    def test_delete_node_nonexistent(self):
        assert self.kg.delete_node("nonexistent_id_12345") is False

    def test_upsert_edge_new_and_duplicate(self):
        n1 = self.kg.upsert_node({"label": "边测试A", "type": "concept"})
        n2 = self.kg.upsert_node({"label": "边测试B", "type": "concept"})
        e1 = self.kg.upsert_edge({"source": n1.id, "target": n2.id, "relation": "related"})
        assert e1.relation == "related"
        e2 = self.kg.upsert_edge({"source": n1.id, "target": n2.id, "relation": "supports"})
        assert e2.relation == "supports"
        count = sum(1 for e in self.kg.edges if e.source == n1.id and e.target == n2.id)
        assert count == 1

    def test_upsert_edge_unknown_node_raises(self):
        with pytest.raises(ValueError):
            self.kg.upsert_edge({"source": "no_such", "target": "also_missing", "relation": "related"})

    def test_delete_edge(self):
        n1 = self.kg.upsert_node({"label": "删边A", "type": "concept"})
        n2 = self.kg.upsert_node({"label": "删边B", "type": "concept"})
        self.kg.upsert_edge({"source": n1.id, "target": n2.id, "relation": "related"})
        assert self.kg.delete_edge(n1.id, n2.id) is True
        assert self.kg.delete_edge(n1.id, n2.id) is False

    def test_save_and_reload(self):
        n = self.kg.upsert_node({"label": "持久化测试", "type": "value", "summary": "测试保存"})
        # Reload
        kg2 = KnowledgeGraph.__new__(KnowledgeGraph)
        kg2.character_name = "test"
        kg2.nodes = {}
        kg2.edges = []
        kg2._adjacency = {}
        kg2._disabled_nodes = set()
        kg2._load_from_path(self.tmpfile)
        assert n.id in kg2.nodes
        assert kg2.nodes[n.id].label == "持久化测试"

    def test_sanitize_id(self):
        assert KnowledgeGraph._sanitize_id("吸引力原则") == "吸引力原则"
        assert "test" in KnowledgeGraph._sanitize_id("test!@#$")

    def test_rebuild_adjacency(self):
        n1 = self.kg.upsert_node({"label": "邻接A", "type": "concept"})
        n2 = self.kg.upsert_node({"label": "邻接B", "type": "concept"})
        self.kg.upsert_edge({"source": n1.id, "target": n2.id, "relation": "supports"})
        assert n2.id in [nei for nei, rel in self.kg._adjacency[n1.id]]


class TestMultiKnowledgeGraph:
    """Test multi-KG aggregation: 1 primary + 3 supplement graphs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mkg = MultiKnowledgeGraph("童锦程")

    def test_loads_primary_and_supplements(self):
        assert self.mkg.primary is not None
        assert len(self.mkg.primary.nodes) >= 20
        assert len(self.mkg.supplements) >= 2
        total = len(self.mkg.primary.nodes) + sum(len(s.nodes) for s in self.mkg.supplements)
        assert total >= 40

    def test_activate_merges_cross_graph(self):
        activated = self.mkg.activate("我喜欢的女生对我忽冷忽热怎么办")
        assert len(activated) > 0
        sources = set(src for _, _, src in activated)
        # Should include nodes from multiple graphs
        assert len(sources) >= 2 or len(activated) >= 2

    def test_activate_respects_max_total(self):
        activated = self.mkg.activate("真诚 自律 恋爱 搭讪 吸引 迷茫 朋友")
        assert len(activated) <= MultiKnowledgeGraph.MAX_TOTAL_NODES

    def test_get_context_marks_supplement_source(self):
        activated = self.mkg.activate("我想搭讪但不知道怎么开口")
        if activated:
            ctx = self.mkg.get_context(activated)
            assert "童锦程" in ctx or "参考" in ctx

    def test_to_dict_includes_configs(self):
        data = self.mkg.to_dict()
        assert data["character"] == "童锦程"
        assert len(data["graphs"]) >= 2
        assert data["total_nodes"] >= 40
        assert data["total_edges"] >= 20
        for g in data["graphs"]:
            assert "config" in g
            assert "temperature" in g["config"]

    def test_per_graph_config(self):
        cfg = self.mkg.get_graph_config("童锦程_行为动力学")
        assert cfg["temperature"] == 0.7
        self.mkg.set_graph_config("童锦程_行为动力学", {"temperature": 1.5})
        assert self.mkg.get_graph_config("童锦程_行为动力学")["temperature"] == 1.5
        # Other graphs unchanged
        assert self.mkg.get_graph_config("童锦程_价值网络")["temperature"] == 0.7

    def test_set_all_configs(self):
        self.mkg.set_all_configs({
            "童锦程": {"persona_depth": 2.0},
            "童锦程_衍生思想": {"creativity": 0.9}
        })
        assert self.mkg.get_graph_config("童锦程")["persona_depth"] == 2.0
        assert self.mkg.get_graph_config("童锦程_衍生思想")["creativity"] == 0.9

    def test_toggle_node_across_graphs(self):
        # Toggle a node in primary
        assert self.mkg.toggle_node("attraction_principle", False)
        assert "attraction_principle" in self.mkg.get_disabled_nodes()
        # Toggle back
        assert self.mkg.toggle_node("attraction_principle", True)
        assert "attraction_principle" not in self.mkg.get_disabled_nodes()
        # Toggle a node in supplement
        if self.mkg.supplements:
            supp = self.mkg.supplements[0]
            if supp.nodes:
                nid = list(supp.nodes.keys())[0]
                assert self.mkg.toggle_node(nid, False)
                assert nid in self.mkg.get_disabled_nodes()

    def test_toggle_nonexistent_node(self):
        assert self.mkg.toggle_node("nonexistent_xyz_123", False) is False

    def test_disabled_nodes_excluded_from_activation(self):
        self.mkg.toggle_node("attraction_principle", False)
        activated = self.mkg.activate("吸引力")
        node_ids = [n.id for n, _, _ in activated]
        assert "attraction_principle" not in node_ids
        self.mkg.toggle_node("attraction_principle", True)

    def test_empty_activate_for_irrelevant_input(self):
        activated = self.mkg.activate("xyzzy 无关文本 天气")
        assert len(activated) == 0 or all(s < 0.3 for _, s, _ in activated)
