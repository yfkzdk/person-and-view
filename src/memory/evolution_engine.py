"""
进化引擎：编排三条管线，汇总变更建议。

管线: GapDetector → KnowledgeSupplement → ConsistencyGuard → 候选变更

每 N 轮触发一次（默认 15），产出候选节点+边写入 session_settings["evolution"]["pending"]。
前端面板展示候选，用户确认后由 API 注入 MultiKnowledgeGraph。
"""
from typing import List, Dict, Optional, Set
import logging

from src.memory.gap_detector import detect_gaps
from src.memory.knowledge_supplement import search_skill_knowledge
from src.memory.consistency_guard import check_consistency, CheckResult

logger = logging.getLogger(__name__)

# Evolution guardrails
MAX_NEW_NODES_PER_ROUND = 2
MAX_NEW_EDGES_PER_ROUND = 1
MAX_EVOLUTION_NODES_TOTAL = 10
EVOLUTION_TRIGGER_INTERVAL = 15  # 每 N 轮触发
REJECT_BLACKLIST_TURNS = 30  # 拒绝的 gap 冷却轮数


def run_evolution_cycle(
    settings: Dict,
    character_name: str = "童锦程",
    skill_repo_path: str = None,
    force: bool = False,
    existing_nodes: Dict[str, any] = None,
    existing_edges: List[any] = None
) -> Dict:
    """
    执行一轮进化检测，返回候选变更摘要。

    Args:
        settings: session_settings，包含 knowledge.evolution 存储结构
        character_name: 角色名
        skill_repo_path: skill 库路径
        force: 强制执行（忽略轮数阈值）
        existing_nodes: 已有节点 dict {node_id: KGNode}，用于一致性检查
        existing_edges: 已有边列表，用于避免重复 contradicts

    Returns:
        {
            "triggered": bool,         # 本轮是否触发进化
            "reason": str,             # 触发原因 / 未触发原因
            "candidates": [...],       # 候选节点列表（含 _check 结果）
            "stats": {
                "gaps_found": int,
                "supplement_matches": int,
                "passed_guard": int,
                "rejected_by_guard": int,
                "evolution_round": int,
                "total_evolution_nodes": int
            }
        }
    """
    existing_nodes = existing_nodes or {}
    existing_edges = existing_edges or []

    # 确保 evolution 结构存在
    evolution = _ensure_evolution_structure(settings)

    stats = {
        "gaps_found": 0,
        "supplement_matches": 0,
        "passed_guard": 0,
        "rejected_by_guard": 0,
        "evolution_round": evolution.get("evolution_round", 0),
        "total_evolution_nodes": len(evolution.get("history", [])),
    }

    # 检查是否达到触发间隔
    signal_buffer = evolution.get("signal_buffer", [])
    turn_counter = evolution.get("_turn_counter", 0)

    if not force:
        last_evolution_turn = evolution.get("_last_evolution_turn", 0)
        turns_since_last = turn_counter - last_evolution_turn
        if turns_since_last < EVOLUTION_TRIGGER_INTERVAL:
            return {
                "triggered": False,
                "reason": f"还需 {EVOLUTION_TRIGGER_INTERVAL - turns_since_last} 轮触发进化（当前间隔 {turns_since_last}/{EVOLUTION_TRIGGER_INTERVAL}）",
                "candidates": [],
                "stats": stats
            }

    # 检查进化节点上限
    history_count = len(evolution.get("history", []))
    if history_count >= MAX_EVOLUTION_NODES_TOTAL:
        return {
            "triggered": False,
            "reason": f"进化节点已达上限 {MAX_EVOLUTION_NODES_TOTAL}，请人工清理后继续",
            "candidates": [],
            "stats": stats
        }

    # Build node labels map for gap detector
    all_node_labels = {}
    if existing_nodes:
        for nid, node in existing_nodes.items():
            all_node_labels[nid] = getattr(node, 'label', nid)

    # --- Pipeline 1: Gap Detection ---
    gaps = detect_gaps(signal_buffer, all_node_labels, max_gaps=3)
    stats["gaps_found"] = len(gaps)

    if not gaps:
        return {
            "triggered": True,
            "reason": "未发现明显知识空白",
            "candidates": [],
            "stats": stats
        }

    # 过滤黑名单中的 gap
    blacklist = evolution.get("rejected_blacklist", {})
    filtered_gaps = []
    for g in gaps:
        concept = g.get("concept", "")
        if concept in blacklist:
            rejected_at = blacklist[concept]
            if turn_counter - rejected_at < REJECT_BLACKLIST_TURNS:
                continue  # 仍在冷却期
            else:
                del blacklist[concept]  # 冷却期过
        filtered_gaps.append(g)
    gaps = filtered_gaps

    if not gaps:
        return {
            "triggered": True,
            "reason": "发现知识空白但均在冷却期内",
            "candidates": [],
            "stats": stats
        }

    # --- Pipeline 2: Knowledge Supplement ---
    candidates = search_skill_knowledge(gaps, skill_repo_path, max_results=5)
    stats["supplement_matches"] = len(candidates)

    if not candidates:
        return {
            "triggered": True,
            "reason": f"发现 {len(gaps)} 个空白但 skill 库无匹配",
            "candidates": [],
            "stats": stats
        }

    # --- Pipeline 3: Consistency Guard ---
    passed = []
    for c in candidates:
        result = check_consistency(c, existing_nodes, character_name, existing_edges)
        c["_check"] = {
            "passed": result.passed,
            "checks": result.checks,
            "suggestions": result.suggestions,
            "contradicts_edge": result.contradicts_edge,
            "merge_target": result.merge_target,
        }
        if result.passed:
            stats["passed_guard"] += 1
            passed.append(c)
        else:
            stats["rejected_by_guard"] += 1
            # 仍然保留在列表中让前端看到拒绝原因
            passed.append(c)

    # Apply guardrails: cap new nodes + edges
    approved_nodes = [c for c in passed if c["_check"]["passed"]]
    approved_nodes = approved_nodes[:MAX_NEW_NODES_PER_ROUND]
    suggested_edges = []
    for c in approved_nodes:
        edge = c["_check"].get("contradicts_edge")
        if edge and len(suggested_edges) < MAX_NEW_EDGES_PER_ROUND:
            suggested_edges.append({
                "source": c.get("label", ""),
                "target": edge["target"],
                "relation": edge["relation"],
                "description": edge.get("description", "")
            })

    # Write to pending (keep all for frontend display)
    evolution["pending"] = passed[:5]
    evolution["_last_evolution_turn"] = turn_counter
    evolution["_pending_edges"] = suggested_edges

    triggered = True
    reason = (
        f"发现 {stats['gaps_found']} 个空白, "
        f"匹配 {stats['supplement_matches']} 个知识概念, "
        f"通过守卫 {stats['passed_guard']} 个, "
        f"拒绝 {stats['rejected_by_guard']} 个"
    )

    return {
        "triggered": triggered,
        "reason": reason,
        "candidates": passed[:5],
        "stats": stats
    }


def confirm_candidate(
    settings: Dict,
    candidate_index: int,
    custom_label: str = None,
    custom_summary: str = None,
    custom_triggers: List[str] = None
) -> Dict:
    """
    确认一个候选节点：从 pending 中取出，记录到 history，返回待注入的数据。

    Returns:
        {"node": {...}, "edge": {...} or None} — 供调用方注入 KG
    """
    evolution = _ensure_evolution_structure(settings)
    pending = evolution.get("pending", [])

    if candidate_index < 0 or candidate_index >= len(pending):
        raise ValueError(f"无效候选索引: {candidate_index} (共 {len(pending)} 个)")

    candidate = pending.pop(candidate_index)

    # Allow user overrides
    node_data = {
        "label": custom_label or candidate.get("label", ""),
        "type": candidate.get("type", "concept"),
        "summary": custom_summary or candidate.get("summary", ""),
        "content": candidate.get("content", ""),
        "triggers": custom_triggers or candidate.get("triggers", [])[:8],
        "tags": candidate.get("tags", []),
        "_source_skill": candidate.get("_source_skill", ""),
        "_gap_concept": candidate.get("_gap_concept", ""),
    }

    # Check for merge target
    edge_data = None
    check = candidate.get("_check", {})
    if check.get("merge_target"):
        # Merging into existing node — no new edge
        node_data["_merge_into"] = check["merge_target"]
    elif check.get("contradicts_edge"):
        edge_data = {
            "source": candidate.get("label", ""),
            "target": check["contradicts_edge"]["target"],
            "relation": "contradicts",
            "description": check["contradicts_edge"].get("description", "")
        }

    # 从 pending_edges 中取对应边
    pending_edges = evolution.get("_pending_edges", [])
    if pending_edges and not edge_data:
        edge_data = pending_edges.pop(0) if pending_edges else None

    # Record in history
    history_entry = {
        "node": node_data,
        "edge": edge_data,
        "confirmed_at_turn": evolution.get("_turn_counter", 0),
        "source_gap": candidate.get("_gap_concept", ""),
    }
    evolution.setdefault("history", []).append(history_entry)

    return {"node": node_data, "edge": edge_data}


def reject_candidate(settings: Dict, candidate_index: int) -> Dict:
    """
    拒绝一个候选节点：从 pending 中移除，写入黑名单冷却 30 轮。

    Returns:
        {"rejected": str (gap_concept), "cooldown_turns": int}
    """
    evolution = _ensure_evolution_structure(settings)
    pending = evolution.get("pending", [])

    if candidate_index < 0 or candidate_index >= len(pending):
        raise ValueError(f"无效候选索引: {candidate_index} (共 {len(pending)} 个)")

    candidate = pending.pop(candidate_index)
    gap_concept = candidate.get("_gap_concept", candidate.get("label", ""))

    # Add to blacklist with current turn
    blacklist = evolution.setdefault("rejected_blacklist", {})
    blacklist[gap_concept] = evolution.get("_turn_counter", 0)

    return {
        "rejected": gap_concept,
        "cooldown_turns": REJECT_BLACKLIST_TURNS
    }


def get_evolution_status(settings: Dict) -> Dict:
    """
    获取当前进化状态摘要（供 GET API + 前端面板轮询）。

    Returns:
        {pending, history, health, stats}
    """
    evolution = _ensure_evolution_structure(settings)

    pending = evolution.get("pending", [])
    history = evolution.get("history", [])
    blacklist = evolution.get("rejected_blacklist", {})
    turn_counter = evolution.get("_turn_counter", 0)

    # Clean expired blacklist entries
    expired = [k for k, v in blacklist.items() if turn_counter - v >= REJECT_BLACKLIST_TURNS]
    for k in expired:
        del blacklist[k]

    health = {
        "total_evolution_nodes": len(history),
        "max_evolution_nodes": MAX_EVOLUTION_NODES_TOTAL,
        "locked": len(history) >= MAX_EVOLUTION_NODES_TOTAL,
        "pending_count": len(pending),
        "blacklist_count": len(blacklist),
        "turns_since_last_evolution": turn_counter - evolution.get("_last_evolution_turn", 0),
        "next_evolution_in": max(0, EVOLUTION_TRIGGER_INTERVAL - (turn_counter - evolution.get("_last_evolution_turn", 0))),
        "signal_buffer_size": len(evolution.get("signal_buffer", [])),
    }

    return {
        "pending": pending,
        "history": history[-20:],  # 最近 20 条
        "health": health,
        "evolution_round": evolution.get("evolution_round", 0),
    }


def cleanup_evolution_nodes(settings: Dict, keep_ids: List[str] = None) -> int:
    """
    清理进化节点历史。

    Args:
        keep_ids: 保留的节点 source_gap 列表，不在此列表中的全部移除

    Returns:
        移除数量
    """
    evolution = _ensure_evolution_structure(settings)
    history = evolution.get("history", [])
    if not keep_ids:
        removed = len(history)
        evolution["history"] = []
        return removed

    keep_set = set(keep_ids)
    before = len(history)
    evolution["history"] = [h for h in history if h.get("source_gap", "") in keep_set]
    return before - len(evolution["history"])


def _ensure_evolution_structure(settings: Dict) -> Dict:
    """确保 settings 中存在 evolution 存储结构。"""
    if "knowledge" not in settings:
        settings["knowledge"] = {}
    knowledge = settings["knowledge"]
    if "evolution" not in knowledge:
        knowledge["evolution"] = {
            "signal_buffer": [],
            "evolution_round": 0,
            "pending": [],
            "history": [],
            "rejected_blacklist": {},
            "_turn_counter": 0,
            "_last_evolution_turn": 0,
        }
    return knowledge["evolution"]
