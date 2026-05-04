"""
知识补充器：gap → skill 库搜索 → 角色口吻改写 → 候选节点。

对每个 gap，从 skill 库中搜索匹配的知识概念，用角色口吻改写后返回候选节点。
"""
import os
import json
import re
from typing import List, Dict, Optional
from pathlib import Path


# skill 库的搜索索引（合并 persona-skills.md 摘要 + 本地 SKILL.md 节点）
_SKILL_INDEX: Optional[Dict[str, List[Dict]]] = None


def _build_skill_index(skill_repo_path: str = None) -> Dict[str, List[Dict]]:
    """
    构建 skill 库的搜索索引。
    索引结构: { skill_name: [{label, type, summary, triggers, tags}] }
    """
    global _SKILL_INDEX
    if _SKILL_INDEX is not None:
        return _SKILL_INDEX

    index = {}

    if skill_repo_path is None:
        # 默认路径：人物skill 仓库
        skill_repo_path = "O:/AII/人物skill/awesome-ai-persona-skills-main/awesome-ai-persona-skills-main"

    base = Path(skill_repo_path)
    if not base.exists():
        _SKILL_INDEX = index
        return index

    # 1. 扫描 Novelists/ 和 zimeiti/ 下的 SKILL.md
    for skill_md in base.rglob("SKILL.md"):
        skill_name = skill_md.parent.name.replace("-skill", "").replace("-perspective", "")
        try:
            concepts = _parse_skill_md_light(skill_md)
            if concepts:
                index[skill_name] = concepts
        except Exception:
            pass

    # 2. 从 persona-skills.md 摘要中提取 skill 信息
    catalog_md = base / "persona-skills.md"
    if catalog_md.exists():
        catalog_entries = _parse_catalog(catalog_md)
        for name, info in catalog_entries.items():
            if name not in index:
                # 从目录摘要创建基础条目
                index[name] = [{
                    "label": info.get("name", name),
                    "type": "concept",
                    "summary": info.get("description", "")[:120],
                    "triggers": info.get("triggers", []),
                    "tags": info.get("tags", [])
                }]

    _SKILL_INDEX = index
    return index


def _parse_skill_md_light(filepath: Path) -> List[Dict]:
    """轻量解析 SKILL.md，提取概念摘要（不依赖 skill_parser）。"""
    text = filepath.read_text(encoding="utf-8")

    # 提取 frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    frontmatter = {}
    if fm_match:
        try:
            import yaml
            frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        except Exception:
            pass

    desc = frontmatter.get("description", "")
    # 提取触发词
    triggers = re.findall(r"「(.+?)」", desc)

    concepts = []
    # 提取心智模型名
    model_pattern = re.compile(r"###\s*(?:模型\d+[：:]|Model\s*\d+[：:])\s*(.+)")
    for m in model_pattern.finditer(text):
        name = m.group(1).strip().rstrip("——").strip()
        # 找该模型下的核心描述
        concepts.append({
            "label": name[:60],
            "type": "concept",
            "summary": desc[:120],
            "triggers": triggers[:5],
            "tags": []
        })

    if not concepts and desc:
        concepts.append({
            "label": frontmatter.get("name", "").replace("-perspective", ""),
            "type": "concept",
            "summary": desc[:120],
            "triggers": triggers[:5],
            "tags": []
        })

    return concepts


def _parse_catalog(catalog_path: Path) -> Dict[str, Dict]:
    """解析 persona-skills.md 目录提取 skill 信息。"""
    entries = {}
    text = catalog_path.read_text(encoding="utf-8")
    # 解析表格行: | Skill 名称 | 核心功能 | ... |
    table_rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", text)
    for name, desc in table_rows:
        name = name.strip()
        desc = desc.strip()
        if name.startswith("Skill") or name.startswith("---") or not name:
            continue
        # 提取触发词和标签
        triggers = [t.strip() for t in re.findall(r"「(.+?)」", desc)]
        entries[name.replace(".skill", "").replace(".Skill", "")] = {
            "name": name,
            "description": desc,
            "triggers": triggers,
            "tags": []
        }
    return entries


def search_skill_knowledge(
    gaps: List[Dict],
    skill_repo_path: str = None,
    max_results: int = 5
) -> List[Dict]:
    """
    对每个 gap，从 skill 库搜索匹配的知识概念。

    Args:
        gaps: 来自 gap_detector.detect_gaps() 的输出
        skill_repo_path: skill 库根目录
        max_results: 最多返回几个候选

    Returns:
        candidate_nodes: [{"label", "type", "summary", "content", "triggers", "tags", "_source_skill", "_gap_concept"}]
    """
    index = _build_skill_index(skill_repo_path)
    candidates = []

    for gap in gaps:
        concept = gap.get("concept", "")
        related = gap.get("related_nodes", [])
        context = gap.get("context", "")

        # 搜索：concept 与 skill 摘要的文本匹配
        matches = _search_index(concept, index, top_k=3)

        for match in matches:
            skill_name = match["skill_name"]
            entry = match["entry"]
            # 用角色口吻改写（简化版：添加角色相关上下文）
            rewritten = _rewrite_in_character_voice(entry, concept, context)

            candidates.append({
                "label": rewritten["label"],
                "type": entry.get("type", "concept"),
                "summary": rewritten["summary"],
                "content": rewritten["content"],
                "triggers": rewritten["triggers"],
                "tags": entry.get("tags", []),
                "_source_skill": skill_name,
                "_gap_concept": concept,
                "_match_score": match["score"]
            })

    # 去重（按 label）
    seen = set()
    unique = []
    for c in sorted(candidates, key=lambda x: x["_match_score"], reverse=True):
        if c["label"] not in seen:
            seen.add(c["label"])
            unique.append(c)

    return unique[:max_results]


def _search_index(query: str, index: Dict[str, List[Dict]], top_k: int = 3) -> List[Dict]:
    """在 skill 索引中搜索匹配。"""
    results = []

    for skill_name, concepts in index.items():
        for entry in concepts:
            score = _text_match_score(query, entry)
            if score > 0:
                results.append({
                    "skill_name": skill_name,
                    "entry": entry,
                    "score": score
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def _text_match_score(query: str, entry: Dict) -> float:
    """简单文本匹配打分（后续升级为 embedding cos_sim）。"""
    text = (entry.get("label", "") + " " +
            entry.get("summary", "") + " " +
            " ".join(entry.get("triggers", [])) + " " +
            " ".join(entry.get("tags", [])))

    query_lower = query.lower()
    text_lower = text.lower()

    # 精确子串匹配
    if query_lower in text_lower:
        return 0.8

    # 单字重叠率
    query_chars = set(query_lower)
    text_chars = set(text_lower)
    if not query_chars:
        return 0.0
    overlap = len(query_chars & text_chars) / len(query_chars)
    return round(overlap * 0.6, 2)


def _rewrite_in_character_voice(entry: Dict, gap_concept: str, context: str) -> Dict:
    """
    用角色口吻改写 skill 节点的内容。
    简化版：在原文基础上添加角色视角的过渡语。
    后续升级为 LLM 改写。
    """
    label = entry.get("label", gap_concept)
    original_summary = entry.get("summary", "")
    original_triggers = entry.get("triggers", [])

    # Role perspective prefix template
    character_name = "童锦程"
    character_voice_prefix = f"（融入{character_name}视角）关于「{label}」——"

    return {
        "label": label,
        "summary": character_voice_prefix + original_summary[:100],
        "content": f"{original_summary}\n\n应用场景: {context}" if context else original_summary,
        "triggers": list(set(original_triggers + [gap_concept]))[:8]
    }
