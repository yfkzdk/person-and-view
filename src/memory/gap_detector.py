"""
空白检测器：扫描 signal_buffer，发现角色知识覆盖的空白区域。

两种空白类型：
A. 追问未覆盖：用户追问 ≥3 轮，但 KG 激活节点都不直接回答
B. 情绪转折未覆盖：情绪变化 > 0.5 后，用户话语存在未覆盖概念
"""
from typing import List, Dict, Optional
from collections import Counter


# 追问关键词
FOLLOWUP_KEYWORDS = ["为什么", "怎么", "然后呢", "但是", "那如果", "具体呢", "举个例子", "什么意思"]


def detect_gaps(
    signal_buffer: List[Dict],
    all_node_labels: Dict[str, str],  # node_id → label
    max_gaps: int = 3
) -> List[Dict]:
    """
    扫描 signal_buffer，返回 gap_list。

    Args:
        signal_buffer: 最近 50 轮信号
        all_node_labels: {node_id: node_label} 当前全部节点
        max_gaps: 最多产出几个 gap

    Returns:
        gap_list: [{"concept": str, "context": str, "related_nodes": [str], "source": "followup"|"emotion"}]
    """
    gaps = []

    # --- A: 追问未覆盖 ---
    followup_gaps = _detect_followup_gaps(signal_buffer)
    gaps.extend(followup_gaps)

    # --- B: 情绪转折未覆盖 ---
    emotion_gaps = _detect_emotion_gaps(signal_buffer)
    gaps.extend(emotion_gaps)

    # 去重 + 排序（追问优先）
    seen = set()
    unique = []
    for g in gaps:
        if g["concept"] not in seen:
            seen.add(g["concept"])
            unique.append(g)
    gaps = unique[:max_gaps]

    return gaps


def _detect_followup_gaps(buffer: List[Dict]) -> List[Dict]:
    """检测追问中暴露的知识空白。"""
    gaps = []

    # 按时间窗口找连续追问链（≥3 轮追问）
    windows = _find_followup_chains(buffer, min_length=3)

    for chain in windows:
        if len(chain) < 3:
            continue

        # 收集追问中出现的概念词
        concepts = _extract_concept_keywords(chain)
        if not concepts:
            continue

        # 找出追问链中激活节点始终不覆盖的概念
        all_activated = set()
        for sig in chain:
            all_activated.update(sig.get("activated_nodes", []))

        # 如果追问链持续但激活节点少 → 知识空白
        if len(all_activated) <= 2 and len(concepts) >= 1:
            # 用第一个追问的上下文作为 context
            context = _build_context(chain)
            for concept in concepts[:2]:  # 每个链最多 2 个 gap
                gaps.append({
                    "concept": concept,
                    "context": context,
                    "related_nodes": list(all_activated),
                    "source": "followup"
                })

    return gaps


def _detect_emotion_gaps(buffer: List[Dict]) -> List[Dict]:
    """检测情绪转折中暴露的知识空白。"""
    gaps = []

    for i in range(1, len(buffer)):
        sig = buffer[i]
        prev = buffer[i - 1]

        # 情绪变化幅度 > 0.5
        if abs(sig.get("emotion_shift", 0)) > 0.5:
            # 情绪转折后的概念
            concepts = _extract_concept_keywords([sig])
            for concept in concepts:
                gaps.append({
                    "concept": concept,
                    "context": f"情绪转折: {prev.get('emotion_shift', 0):.2f} → {sig.get('emotion_shift', 0):.2f}",
                    "related_nodes": sig.get("activated_nodes", []),
                    "source": "emotion"
                })

    return gaps


def _find_followup_chains(buffer: List[Dict], min_length: int = 3) -> List[List[Dict]]:
    """在 signal_buffer 中找到连续追问链。"""
    chains = []
    current_chain = []

    for sig in buffer:
        if sig.get("followup_detected"):
            current_chain.append(sig)
        else:
            if len(current_chain) >= min_length:
                chains.append(current_chain)
            current_chain = []

    # 末尾可能还有未闭合的链
    if len(current_chain) >= min_length:
        chains.append(current_chain)

    return chains


def _extract_concept_keywords(signals: List[Dict]) -> List[str]:
    """
    从信号中提取核心概念词。
    基于追问关键词 → 概念映射 + user_snippet 中的情绪关键词。
    """
    # 追问关键词 → 概念映射
    followup_to_concept = {
        "为什么": "因果关系分析",
        "怎么": "方法/步骤指导",
        "然后呢": "后续发展推演",
        "但是": "对立/矛盾分析",
        "那如果": "假设推演",
        "具体呢": "细节/具象化",
        "举个例子": "案例/类比思维",
        "什么意思": "概念定义与澄清",
    }

    # 情绪关键词检测（从 user_snippet 中）
    emotion_keywords = {
        "生气": "愤怒管理", "火大": "愤怒管理", "愤怒": "愤怒管理",
        "难过": "悲伤处理", "伤心": "悲伤处理", "哭": "悲伤处理",
        "担心": "焦虑应对", "焦虑": "焦虑应对", "害怕": "恐惧应对",
        "喜欢": "亲密关系", "爱": "亲密关系", "心动": "亲密关系",
        "讨厌": "边界设定", "烦": "边界设定",
        "分手": "失去与告别", "遗憾": "失去与告别",
    }

    concepts = Counter()
    for sig in signals:
        # 从追问词映射
        for kw in sig.get("followup_keywords", []):
            concept = followup_to_concept.get(kw)
            if concept:
                concepts[concept] += 1

        # 从 user_snippet 提取情绪概念
        snippet = sig.get("user_snippet", "")
        for kw, concept in emotion_keywords.items():
            if kw in snippet:
                concepts[concept] += 1

    return [c for c, count in concepts.most_common(5) if count >= 2]


def _build_context(chain: List[Dict]) -> str:
    """从追问链中构建上下文描述。"""
    if not chain:
        return ""
    parts = []
    for i, sig in enumerate(chain[:5]):
        turn = sig.get("turn", i)
        nodes = sig.get("activated_nodes", [])
        parts.append(f"轮{turn}: 追问, 激活节点={nodes}")
    return "; ".join(parts)
