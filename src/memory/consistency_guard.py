"""
一致性守卫：矛盾/重复/人格入侵三重检测。

新节点入库前检查，通过则返回通过标记，否则返回拒绝/合并/矛盾建议。
不依赖 embedding —— 纯文本规则匹配，后续可升级。
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


# 角色核心价值（人格入侵检测用）
CHARACTER_CORE_VALUES = {
    "童锦程": [
        "不跪舔——不讨好、不迎合、不把对方的需求放在自己之上",
        "框架主导——始终由自己定义关系的节奏和边界，不被动接受对方的框架",
        "价值先行——先建立自身价值再谈关系，不空谈感情不付出行动",
        "不自我感动——不做让对方无感甚至反感的自我牺牲式付出",
    ],
    "默认": [
        "一致性——言行前后矛盾会破坏角色可信度",
        "边界感——不过度侵入用户隐私和情感依赖",
    ]
}

# 人格入侵检测关键词（否定核心价值=入侵）
PERSONALITY_INVASION_PATTERNS = {
    "不跪舔": ["讨好对方", "放低自己", "千方百计迎合", "无底线迁就", "以TA为中心"],
    "框架主导": ["被对方主导", "听TA的安排", "你说了算", "失去主动权", "被动接受"],
    "价值先行": ["先追再说", "不管值不值得", "先付出再谈条件", "别想那么多"],
    "不自我感动": ["默默付出", "自我牺牲不求回报", "在TA楼下等一晚上", "折千纸鹤"],
}


@dataclass
class CheckResult:
    """一致性检查结果"""
    passed: bool
    node_label: str
    checks: Dict[str, str] = field(default_factory=dict)
    # "contradiction": node_id — 与哪个已有节点矛盾
    # "duplicate": node_id — 与哪个已有节点高度重复
    # "invasion": core_value_name — 冲击了哪条核心价值（拒绝注入）
    suggestions: List[str] = field(default_factory=list)
    contradicts_edge: Optional[dict] = None  # {target, relation: "contradicts"}
    merge_target: Optional[str] = None  # 建议合并到的已有 node_id


def check_consistency(
    candidate: Dict,
    existing_nodes: Dict[str, any],  # node_id → KGNode
    character_name: str = "童锦程",
    existing_edges: List[any] = None  # KGEdge list
) -> CheckResult:
    """
    对候选节点执行三重一致性检查。

    Args:
        candidate: 候选节点 dict，含 label, summary, content, triggers, tags
        existing_nodes: 已有节点 dict {node_id: KGNode}
        character_name: 角色名，用于加载核心价值
        existing_edges: 已有边列表，用于避免重复创建 contradicts 边

    Returns:
        CheckResult — passed=True 表示可注入，passed=False 表示被拒绝
    """
    label = candidate.get("label", "")
    summary = candidate.get("summary", "")
    content = candidate.get("content", "")
    triggers = candidate.get("triggers", [])

    result = CheckResult(passed=True, node_label=label)
    existing_edges = existing_edges or []

    # 1. 重复检测
    duplicate_of = _detect_duplicate(label, summary, content, existing_nodes)
    if duplicate_of:
        result.checks["duplicate"] = duplicate_of
        result.merge_target = duplicate_of
        result.passed = False
        result.suggestions.append(f"节点「{label}」与已有节点「{duplicate_of}」高度重复，建议合并而非新建")
        return result

    # 2. 人格入侵检测
    invaded = _detect_personality_invasion(content, summary, character_name)
    if invaded:
        result.checks["invasion"] = invaded
        result.passed = False
        result.suggestions.append(f"节点内容冲击角色核心价值「{invaded}」，拒绝注入")
        return result

    # 3. 矛盾检测（不拒绝，只建议创建 contradicts 边）
    contradiction_of = _detect_contradiction(label, summary, content, existing_nodes, existing_edges)
    if contradiction_of:
        result.checks["contradiction"] = contradiction_of
        result.contradicts_edge = {
            "target": contradiction_of,
            "relation": "contradicts",
            "description": f"「{label}」与「{contradiction_of}」存在观点张力"
        }
        result.suggestions.append(f"节点「{label}」与已有节点「{contradiction_of}」存在观点张力，建议创建 contradicts 边")
        # 不拒绝，让 LLM 感知张力

    return result


def _detect_duplicate(
    label: str,
    summary: str,
    content: str,
    existing_nodes: Dict[str, any]
) -> Optional[str]:
    """
    检测候选节点是否与已有节点高度重复。

    策略：label 完全相同 OR (label 编辑距离 ≤2 且 summary 前 60 字匹配 >80%)
    """
    if not existing_nodes:
        return None

    label_lower = label.strip().lower()
    summary_head = (summary or "")[:60]

    for node_id, node in existing_nodes.items():
        existing_label = (node.label or "").strip().lower()
        existing_summary = (node.summary or "")[:60]

        # 完全同名
        if label_lower == existing_label:
            return node_id

        # label 编辑距离 ≤2
        if _edit_distance(label_lower, existing_label) <= 2:
            # 且 summary 重叠度高
            if _char_overlap(summary_head, existing_summary) > 0.8:
                return node_id

    return None


def _detect_personality_invasion(
    content: str,
    summary: str,
    character_name: str
) -> Optional[str]:
    """
    检测新节点内容是否冲击角色核心价值。

    策略：扫描 content + summary 中是否出现入侵关键词。
    命中任一核心价值的入侵关键词 → 返回该核心价值名。
    """
    core_values = CHARACTER_CORE_VALUES.get(character_name, CHARACTER_CORE_VALUES["默认"])
    patterns = PERSONALITY_INVASION_PATTERNS
    combined_text = (content + " " + summary).lower()

    for core_value in core_values:
        core_name = core_value.split("——")[0].strip()
        invasion_keywords = patterns.get(core_name, [])
        for kw in invasion_keywords:
            if kw.lower() in combined_text:
                return core_name

    return None


def _detect_contradiction(
    label: str,
    summary: str,
    content: str,
    existing_nodes: Dict[str, any],
    existing_edges: List[any]
) -> Optional[str]:
    """
    检测候选节点是否与已有节点存在语义矛盾。

    策略：
    1. 已有 contradicts 边 → 不重复建议
    2. 判断是否存在「对立词对」如 主动↔被动、靠近↔远离
    """
    contradiction_pairs = [
        ("主动", "被动"), ("靠近", "远离"), ("热情", "冷漠"),
        ("付出", "保留"), ("坚持", "放弃"), ("积极", "消极"),
        ("开放", "封闭"), ("信任", "怀疑"), ("直接", "委婉"),
        ("理性", "感性"), ("进攻", "防守"), ("主导", "服从"),
    ]

    combined = (label + summary + content).lower()

    for node_id, node in existing_nodes.items():
        existing_text = (node.label + node.summary + node.content).lower()

        # 跳过已有 contradicts 边的
        already_contradicts = any(
            (e.source == candidate_new_id(label) and e.target == node_id and e.relation == "contradicts") or
            (e.target == candidate_new_id(label) and e.source == node_id and e.relation == "contradicts")
            for e in existing_edges
        )
        if already_contradicts:
            continue

        # 检查矛盾词对
        for a, b in contradiction_pairs:
            if a in combined and b in existing_text:
                return node_id
            if b in combined and a in existing_text:
                return node_id

    return None


def candidate_new_id(label: str) -> str:
    """生成候选节点 ID（与 knowledge_graph upsert_node 的 sanitize_id 一致）。"""
    import re
    safe = re.sub(r'[^\w一-鿿]', '_', label)
    return safe.lower()[:60] if safe else f"node_{abs(hash(label)) % 10000}"


def merge_candidate_into_existing(
    candidate: Dict,
    target_node_id: str,
    existing_nodes: Dict[str, any]
) -> Dict:
    """
    将候选节点内容合并到已有节点（丰富 content 和 triggers）。

    Returns:
        更新后的 target node 数据 dict
    """
    target = existing_nodes.get(target_node_id)
    if not target:
        return candidate

    merged = {
        "id": target_node_id,
        "label": target.label,
        "type": target.type,
        "summary": target.summary,
        "content": (target.content or "") + "\n\n（补充视角）" + (candidate.get("content", "") or ""),
        "triggers": list(set(list(target.triggers) + candidate.get("triggers", [])))[:12],
        "tags": list(set(list(target.tags) + candidate.get("tags", []))),
    }
    return merged


def _edit_distance(s1: str, s2: str) -> int:
    """Levenshtein 编辑距离（简版，限长度 ≤4 差异时使用）。"""
    if s1 == s2:
        return 0
    if abs(len(s1) - len(s2)) > 4:
        return 999

    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _char_overlap(s1: str, s2: str) -> float:
    """字符级重叠率。"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    set1, set2 = set(s1), set(s2)
    return len(set1 & set2) / max(len(set1 | set2), 1)
