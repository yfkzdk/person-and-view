"""
知识图谱检索器 — 网状角色知识激活与注入

功能：
- 加载角色知识图谱（节点 + 边）
- 基于用户输入触发激活节点
- 激活扩散到邻居节点（衰减传播）
- 生成自然语言上下文注入 LLM
- 支持手动开关节点（供前端面板控制）
- 支持节点/边的 CRUD 编辑并持久化
"""
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
import os
import re

logger = logging.getLogger(__name__)


@dataclass
class KGNode:
    id: str
    type: str  # mental_model, heuristic, value, scene, concept
    label: str
    summary: str
    content: str = ""
    triggers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class KGEdge:
    source: str
    target: str
    relation: str  # supports, derives_from, contradicts, applies_to, related
    description: str = ""


class KnowledgeGraph:
    """
    角色知识图谱。

    Usage:
        kg = KnowledgeGraph("童锦程")
        activated = kg.activate("我喜欢的女生忽冷忽热")
        context = kg.get_context(activated)  # → 自然语言上下文
    """

    # 激活扩散的衰减系数（每跳衰减 0.5）
    SPREAD_DECAY = 0.5
    # 直接触发的最低匹配分
    ACTIVATION_THRESHOLD = 0.3
    # 最大注入节点数
    MAX_INJECT_NODES = 3

    def __init__(self, character_name: str = "童锦程"):
        self.character_name = character_name
        self.nodes: Dict[str, KGNode] = {}
        self.edges: List[KGEdge] = []
        self._adjacency: Dict[str, List[Tuple[str, str]]] = {}
        self._disabled_nodes: Set[str] = set()
        self._filepath: Optional[Path] = None

        self._load(character_name)

    # ---- 加载 ----

    def _load(self, character_name: str):
        """从 JSON 文件加载知识图谱。"""
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "characters" / f"{character_name}_knowledge_graph.json",
            Path(os.getcwd()) / "characters" / f"{character_name}_knowledge_graph.json",
            Path(os.getcwd()) / "app" / "voices" / "characters" / f"{character_name}_knowledge_graph.json",
        ]
        filepath = None
        for p in candidates:
            if p.exists():
                filepath = p
                break

        if not filepath:
            logger.warning(f"Knowledge graph not found for {character_name}, tried: {candidates}")
            return

        self._filepath = filepath
        self._load_from_path(filepath)

    def _load_from_path(self, filepath: Path):
        """从指定路径加载图谱数据。"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for nd in data.get("nodes", []):
            node = KGNode(
                id=nd["id"],
                type=nd["type"],
                label=nd["label"],
                summary=nd["summary"],
                content=nd.get("content", ""),
                triggers=nd.get("triggers", []),
                tags=nd.get("tags", [])
            )
            self.nodes[node.id] = node

        for ed in data.get("edges", []):
            edge = KGEdge(
                source=ed["source"],
                target=ed["target"],
                relation=ed["relation"],
                description=ed.get("description", "")
            )
            self.edges.append(edge)

        self._rebuild_adjacency()

        logger.info(
            f"Loaded knowledge graph for {self.character_name}: "
            f"{len(self.nodes)} nodes, {len(self.edges)} edges"
        )

    # ---- 激活 ----

    def activate(
        self,
        user_text: str,
        max_nodes: int = None
    ) -> List[Tuple[KGNode, float]]:
        """
        根据用户输入激活知识图谱节点。

        算法：
        1. 直接匹配：trigger 词命中 → 计算匹配分
        2. 扩散传播：直接命中的邻居获得衰减后的分数
        3. 按分数排序，返回 top N

        Returns:
            [(node, activation_score), ...] 按分数降序
        """
        if not self.nodes:
            return []

        max_nodes = max_nodes or self.MAX_INJECT_NODES
        scores: Dict[str, float] = {}

        # 第一轮：直接触发匹配
        for node_id, node in self.nodes.items():
            if node_id in self._disabled_nodes:
                continue
            score = self._match_score(user_text, node)
            if score >= self.ACTIVATION_THRESHOLD:
                scores[node_id] = score

        # 第二轮：扩散到邻居
        spread_scores: Dict[str, float] = {}
        for node_id, score in scores.items():
            for neighbor_id, relation in self._adjacency.get(node_id, []):
                if neighbor_id in self._disabled_nodes:
                    continue
                # contradicts 关系不传播（表面矛盾，需要精准匹配才激活）
                if relation == "contradicts":
                    continue
                decay = self.SPREAD_DECAY
                # supports / derives_from 关系更强
                if relation in ("supports", "derives_from"):
                    decay = 0.6
                spread = score * decay
                if neighbor_id not in scores:  # 不覆盖直接命中
                    spread_scores[neighbor_id] = max(
                        spread_scores.get(neighbor_id, 0), spread
                    )

        # 合并分数
        for node_id, spread in spread_scores.items():
            if spread >= self.ACTIVATION_THRESHOLD * 0.7:  # 扩散阈值稍低
                scores[node_id] = spread

        # 排序返回
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(self.nodes[nid], score) for nid, score in ranked[:max_nodes]]

    def _match_score(self, text: str, node: KGNode) -> float:
        """计算文本与节点的匹配分数（0-1）。"""
        if not node.triggers:
            return 0.0

        hits = 0.0
        for trigger in node.triggers:
            if trigger in text:
                # 长触发词权重更高，cap at 2.0 per trigger
                hits += min(len(trigger) / 4, 2.0)

        if hits == 0.0:
            return 0.0

        # Normalize against a fixed cap — ~3 long triggers saturates
        return min(hits / 4.0, 1.0)

    # ---- 上下文生成 ----

    def get_context(
        self,
        activated: List[Tuple[KGNode, float]],
        max_chars: int = 300
    ) -> str:
        """
        将激活节点转化为注入 LLM 的自然语言上下文。

        Args:
            activated: activate() 的返回值
            max_chars: 最大字符数

        Returns:
            自然语言上下文，如：
            "（参考童锦程思路：吸引力原则——没人会因为喜欢他而喜欢你；给台阶——人需要一个能说服自己的理由）"
        """
        if not activated:
            return ""

        parts = []
        for node, score in activated:
            if score >= 0.5:
                parts.append(f"{node.label}——{node.summary}")
            else:
                # 低分节点只给标签提示
                parts.append(f"可参考「{node.label}」")

        joined = "；".join(parts)
        context = f"（本轮可参考童锦程思路：{joined}）"

        if len(context) > max_chars:
            # 截断最后一个完整的分句
            context = context[:max_chars - 3] + "）"

        return context

    # ---- 手动控制（供前端面板） ----

    def toggle_node(self, node_id: str, enabled: bool):
        """手动开关节点。"""
        if node_id not in self.nodes:
            return False
        if enabled:
            self._disabled_nodes.discard(node_id)
        else:
            self._disabled_nodes.add(node_id)
        return True

    def get_disabled_nodes(self) -> List[str]:
        return list(self._disabled_nodes)

    def set_disabled_nodes(self, node_ids: List[str]):
        self._disabled_nodes = set(node_ids)

    # ---- 一致性检查（供进化引擎） ----

    def check_consistency(self, candidate: dict) -> dict:
        """
        对候选节点执行一致性检查（委托 consistency_guard）。

        Args:
            candidate: {"label", "summary", "content", "triggers", "tags"}

        Returns:
            {"passed": bool, "checks": {...}, "suggestions": [...],
             "contradicts_edge": {...} or None, "merge_target": str or None}
        """
        from src.memory.consistency_guard import check_consistency as _check
        result = _check(
            candidate,
            self.nodes,
            self.character_name,
            self.edges
        )
        return {
            "passed": result.passed,
            "checks": result.checks,
            "suggestions": result.suggestions,
            "contradicts_edge": result.contradicts_edge,
            "merge_target": result.merge_target,
        }

    # ---- 完整图谱导出（供前端可视化） ----

    def to_dict(self) -> Dict:
        """导出完整图谱数据供前端渲染。"""
        return {
            "character": self.character_name,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "summary": n.summary,
                    "content": n.content,
                    "triggers": n.triggers,
                    "tags": n.tags,
                    "disabled": n.id in self._disabled_nodes
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "description": e.description
                }
                for e in self.edges
            ]
        }

    # ---- CRUD 编辑（供设置面板） ----

    def _rebuild_adjacency(self):
        """重建邻接表。"""
        self._adjacency = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            if edge.source in self._adjacency and edge.target in self._adjacency:
                self._adjacency[edge.source].append((edge.target, edge.relation))
                self._adjacency[edge.target].append((edge.source, edge.relation))

    @staticmethod
    def _sanitize_id(label: str) -> str:
        """从中文标签生成合法的节点 ID。"""
        # 保留中英文和数字，其余替换为下划线
        safe = re.sub(r'[^\w一-鿿]', '_', label)
        return safe.lower()[:60] if safe else f"node_{abs(hash(label)) % 10000}"

    def upsert_node(self, data: dict) -> KGNode:
        """添加或更新节点。data 含 id 时为更新，否则新建。"""
        node_id = data.get("id") or self._sanitize_id(data.get("label", ""))
        node = KGNode(
            id=node_id,
            type=data.get("type", "concept"),
            label=data.get("label", ""),
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            triggers=data.get("triggers", []),
            tags=data.get("tags", [])
        )
        is_new = node_id not in self.nodes
        self.nodes[node_id] = node
        if is_new:
            self._adjacency[node_id] = []
        logger.info(f"{'Added' if is_new else 'Updated'} node: {node_id}")
        self.save()
        return node

    def delete_node(self, node_id: str) -> bool:
        """删除节点及其所有关联边。"""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        self._disabled_nodes.discard(node_id)
        # 移除关联边
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        self._rebuild_adjacency()
        logger.info(f"Deleted node: {node_id}")
        self.save()
        return True

    def upsert_edge(self, data: dict) -> KGEdge:
        """添加边（去重：同 source+target 视为更新）。"""
        source = data.get("source", "")
        target = data.get("target", "")
        relation = data.get("relation", "related")
        description = data.get("description", "")

        if source not in self.nodes or target not in self.nodes:
            raise ValueError(f"Edge references unknown node: {source} -> {target}")

        # 去重：同 source+target 更新 relation
        existing = None
        for e in self.edges:
            if e.source == source and e.target == target:
                existing = e
                break
        if existing:
            existing.relation = relation
            existing.description = description
            self._rebuild_adjacency()
            logger.info(f"Updated edge: {source} -> {target}")
            self.save()
            return existing

        edge = KGEdge(source=source, target=target, relation=relation, description=description)
        self.edges.append(edge)
        self._adjacency[source].append((target, relation))
        self._adjacency[target].append((source, relation))
        logger.info(f"Added edge: {source} -> {target}")
        self.save()
        return edge

    def delete_edge(self, source: str, target: str) -> bool:
        """删除边。"""
        before = len(self.edges)
        self.edges = [e for e in self.edges if not (e.source == source and e.target == target)]
        if len(self.edges) < before:
            self._rebuild_adjacency()
            logger.info(f"Deleted edge: {source} -> {target}")
            self.save()
            return True
        return False

    def save(self):
        """将当前图谱序列化写回 JSON 文件。"""
        if not self._filepath:
            logger.warning("No filepath set — cannot save knowledge graph")
            return
        data = {
            "character": self.character_name,
            "version": "1.0",
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "summary": n.summary,
                    "content": n.content,
                    "triggers": n.triggers,
                    "tags": n.tags
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "description": e.description
                }
                for e in self.edges
            ]
        }
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved knowledge graph: {len(self.nodes)} nodes, {len(self.edges)} edges")


# ---- 多图谱聚合 ----

MULTI_GRAPH_CONFIG = {
    "童锦程": {
        "primary": "童锦程",
        "supplements": [
            "童锦程_行为动力学", "童锦程_价值网络", "童锦程_衍生思想",
            "童锦程_七情六欲", "童锦程_纳瓦尔", "童锦程_费曼",
            "童锦程_郭德纲", "童锦程_张爱玲"
        ]
    }
}


class MultiKnowledgeGraph:
    """
    管理一个主图谱 + 多个补充子图谱，提供统一激活和聚合。

    Usage:
        mkg = MultiKnowledgeGraph("童锦程")
        activated = mkg.activate("我喜欢的女生忽冷忽热")
        context = mkg.get_context(activated)  # 主 + 子 合并上下文
    """

    MAX_TOTAL_NODES = 6  # 所有图谱合计最多注入节点数

    DEFAULT_GRAPH_CONFIG = {
        "temperature": 0.7,
        "creativity": 0.5,
        "persona_depth": 1.0
    }

    def __init__(self, character_name: str = "童锦程"):
        self.character_name = character_name
        self.primary: Optional[KnowledgeGraph] = None
        self.supplements: List[KnowledgeGraph] = []
        self.graph_configs: Dict[str, Dict] = {}  # graph_name → {temperature, creativity, persona_depth}
        self._load_all(character_name)

    def _load_all(self, character_name: str):
        """加载主图谱和所有子图谱。"""
        config = MULTI_GRAPH_CONFIG.get(character_name, {})
        primary_name = config.get("primary", character_name)
        supplement_names = config.get("supplements", [])

        self.primary = KnowledgeGraph(primary_name)
        self.graph_configs[primary_name] = dict(self.DEFAULT_GRAPH_CONFIG)
        logger.info(f"[MultiKG] Loaded primary: {primary_name} ({len(self.primary.nodes)} nodes)")

        for sname in supplement_names:
            kg = KnowledgeGraph(sname)
            if kg.nodes:
                self.supplements.append(kg)
                self.graph_configs[sname] = dict(self.DEFAULT_GRAPH_CONFIG)
                logger.info(f"[MultiKG] Loaded supplement: {sname} ({len(kg.nodes)} nodes)")
            else:
                logger.warning(f"[MultiKG] Supplement '{sname}' returned empty — file missing or invalid")

    def activate(self, user_text: str) -> List[Tuple[KGNode, float, str]]:
        """
        从所有图谱激活节点，按分数合并排序。

        Returns:
            [(node, score, graph_label), ...] 按分数降序
        """
        all_activated: List[Tuple[KGNode, float, str]] = []

        # 主图谱激活（无上限，后续截断）
        if self.primary and self.primary.nodes:
            primary_results = self.primary.activate(user_text, max_nodes=10)
            for node, score in primary_results:
                all_activated.append((node, score, self.primary.character_name))

        # 子图谱激活
        for kg in self.supplements:
            if not kg.nodes:
                continue
            results = kg.activate(user_text, max_nodes=4)
            for node, score in results:
                all_activated.append((node, score, kg.character_name))

        # 按分数排序，取总上限
        all_activated.sort(key=lambda x: x[1], reverse=True)
        return all_activated[:self.MAX_TOTAL_NODES]

    def get_context(self, activated: List[Tuple[KGNode, float, str]], max_chars: int = 500) -> str:
        """
        将多图谱激活节点转化为分层自然语言上下文。

        主图谱节点在前、高置信度展示；子图谱节点标记来源。
        """
        if not activated:
            return ""

        primary_parts = []
        supplement_parts = []

        for node, score, source in activated:
            is_primary = (source == self.primary.character_name if self.primary else False)
            if is_primary:
                if score >= 0.5:
                    primary_parts.append(f"{node.label}——{node.summary}")
                else:
                    primary_parts.append(f"可参考「{node.label}」")
            else:
                # 子图谱：标记来源
                graph_name = source.replace("童锦程_", "").replace("_knowledge_graph", "")
                if score >= 0.4:
                    supplement_parts.append(f"「{node.label}」({graph_name}): {node.summary}")

        all_parts = primary_parts + supplement_parts
        if not all_parts:
            return ""

        joined = "；".join(all_parts)
        context = f"（本轮可参考童锦程思路：{joined}）"

        if len(context) > max_chars:
            context = context[:max_chars - 3] + "）"

        return context

    def to_dict(self) -> Dict:
        """导出所有图谱数据，包含 per-graph 配置（供前端可视化）。"""
        graphs = []
        if self.primary:
            gd = self.primary.to_dict()
            gd["config"] = self.graph_configs.get(self.primary.character_name, dict(self.DEFAULT_GRAPH_CONFIG))
            graphs.append(gd)
        for kg in self.supplements:
            gd = kg.to_dict()
            gd["config"] = self.graph_configs.get(kg.character_name, dict(self.DEFAULT_GRAPH_CONFIG))
            graphs.append(gd)
        return {
            "character": self.character_name,
            "graphs": graphs,
            "total_nodes": sum(len(g.get("nodes", [])) for g in graphs),
            "total_edges": sum(len(g.get("edges", [])) for g in graphs)
        }

    # ---- per-graph 配置管理 ----

    def get_graph_config(self, graph_name: str) -> Dict:
        """获取指定子图谱的配置。"""
        return self.graph_configs.get(graph_name, dict(self.DEFAULT_GRAPH_CONFIG))

    def set_graph_config(self, graph_name: str, config: Dict):
        """更新指定子图谱的配置（deep merge）。"""
        if graph_name not in self.graph_configs:
            self.graph_configs[graph_name] = dict(self.DEFAULT_GRAPH_CONFIG)
        for key in ("temperature", "creativity", "persona_depth"):
            if key in config:
                self.graph_configs[graph_name][key] = config[key]

    def get_all_configs(self) -> Dict[str, Dict]:
        """获取所有图谱的配置。"""
        return dict(self.graph_configs)

    def set_all_configs(self, configs: Dict[str, Dict]):
        """批量设置图谱配置。"""
        for graph_name, cfg in configs.items():
            self.set_graph_config(graph_name, cfg)

    def get_disabled_nodes(self) -> List[str]:
        """汇总所有图谱的禁用节点。"""
        disabled = []
        if self.primary:
            disabled.extend(self.primary.get_disabled_nodes())
        for kg in self.supplements:
            disabled.extend(kg.get_disabled_nodes())
        return disabled

    def toggle_node(self, node_id: str, enabled: bool) -> bool:
        """在对应图谱中切换节点状态。"""
        for kg in ([self.primary] if self.primary else []) + self.supplements:
            if node_id in kg.nodes:
                return kg.toggle_node(node_id, enabled)
        return False

    def set_disabled_nodes(self, node_ids: List[str]):
        """在所有图谱中设置禁用节点。"""
        for kg in ([self.primary] if self.primary else []) + self.supplements:
            kg.set_disabled_nodes([nid for nid in node_ids if nid in kg.nodes])

    # ---- 一致性检查（供进化引擎） ----

    def check_consistency(self, candidate: dict) -> dict:
        """对候选节点执行一致性检查（委托 primary 图谱）。"""
        if self.primary:
            return self.primary.check_consistency(candidate)
        return {"passed": True, "checks": {}, "suggestions": [], "contradicts_edge": None, "merge_target": None}

    def get_all_nodes_and_edges(self) -> tuple:
        """汇总所有图谱的节点和边（供进化引擎一致性检查）。"""
        all_nodes = {}
        all_edges = []
        for kg in ([self.primary] if self.primary else []) + self.supplements:
            all_nodes.update(kg.nodes)
            all_edges.extend(kg.edges)
        return all_nodes, all_edges
