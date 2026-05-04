"""
Skill 解析器：读取 SKILL.md 或 skill JSON → 输出结构化知识概念列表。

支持的输入格式：
1. SKILL.md (YAML frontmatter + 心智模型 sections)
2. skill JSON ({name, description, triggers, mental_models: [...]})
"""
import re
import yaml
import json
from pathlib import Path
from typing import List, Dict, Optional


def parse_skill_md(filepath: str) -> List[Dict]:
    """解析 SKILL.md 文件，提取心智模型为 KG 节点候选。"""
    text = Path(filepath).read_text(encoding="utf-8")

    # 提取 YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    frontmatter = {}
    if fm_match:
        frontmatter = yaml.safe_load(fm_match.group(1)) or {}

    # 提取描述中的触发词
    desc = frontmatter.get("description", "")
    global_triggers = []
    # 触发词在「」中
    quoted_triggers = re.findall(r"「(.+?)」", desc)
    if quoted_triggers:
        global_triggers = [t.strip() for t in quoted_triggers]
    # 如果没有「」格式，尝试用顿号逗号分割
    if not global_triggers:
        trigger_match = re.search(r"触发词[：:]\s*(.+?)(?:。|\n|$)", desc)
        if trigger_match:
            trigger_text = trigger_match.group(1)
            global_triggers = [t.strip() for t in re.split(r"[、，,]", trigger_text) if t.strip()]

    # 提取身份卡中的核心金句
    taglines = []
    tagline_matches = re.findall(r"^>\s*「(.+?)」", text, re.MULTILINE)
    taglines = tagline_matches[:3]

    # 提取 心智模型 区域
    model_sections = re.split(r"\n### 模型\d+[：:]", text)
    if len(model_sections) < 2:
        # 尝试英文标题格式
        model_sections = re.split(r"\n### Model \d+[：:]", text)
    if len(model_sections) < 2:
        model_sections = re.split(r"\n###\s+(?!Step|身份|回答|表达|创作|问题|核)[^\n]+", text)

    concepts = []
    for idx, section in enumerate(model_sections[1:], 1):
        concept = _extract_concept(section, idx, global_triggers, taglines)
        if concept and concept.get("label"):
            concepts.append(concept)

    # 如果没有心智模型章节，尝试从描述和触发词构建单个概念
    if not concepts and frontmatter.get("description"):
        concepts.append({
            "label": frontmatter.get("name", "").replace("-perspective", "").replace("-skill", ""),
            "type": "concept",
            "summary": frontmatter.get("description", "")[:100],
            "content": frontmatter.get("description", ""),
            "triggers": global_triggers,
            "tags": []
        })

    return concepts


def parse_skill_json(filepath: str) -> List[Dict]:
    """解析 skill JSON 文件（简化格式，用于没有完整 SKILL.md 的 skill）。"""
    data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    concepts = []
    for mm in data.get("mental_models", []):
        concepts.append({
            "label": mm.get("name", ""),
            "type": mm.get("type", "concept"),
            "summary": mm.get("core", "")[:120],
            "content": mm.get("application", ""),
            "triggers": mm.get("triggers", []),
            "tags": mm.get("tags", []),
            "_source_evidence": mm.get("evidence", ""),
            "_limitations": mm.get("limitations", "")
        })
    return concepts


def _extract_concept(section: str, idx: int, global_triggers: List[str], taglines: List[str]) -> Optional[Dict]:
    """从心智模型 section 提取单个概念。"""
    lines = section.strip().split("\n")

    # 提取模型名（第一行通常是标题）
    name = lines[0].strip().rstrip("——").strip()
    if len(name) > 60:
        name = name[:60]

    # 提取 核心、应用方式、来源证据、局限性
    core = ""
    application = ""
    evidence = ""
    limitations = ""

    current_field = None
    fields = {
        "核心": "core",
        "应用方式": "application",
        "来源证据": "evidence",
        "局限性": "limitations",
    }

    for line in lines[1:]:
        stripped = line.strip()
        for cn_field, en_field in fields.items():
            if stripped.startswith(f"**{cn_field}**") or stripped.startswith(f"**{cn_field}："):
                current_field = en_field
                stripped = re.sub(rf"^\*\*{cn_field}[：:]*\*\*\s*", "", stripped)
                break

        if current_field == "core" and stripped and not stripped.startswith("**"):
            core += stripped + " "
        elif current_field == "application" and stripped and not stripped.startswith("**"):
            application += stripped + " "
        elif current_field == "evidence" and stripped and not stripped.startswith("**"):
            evidence += stripped + " "
        elif current_field == "limitations" and stripped and not stripped.startswith("**"):
            limitations += stripped + " "

    core = core.strip()
    application = application.strip()

    if not core:
        return None

    # 提取本模型的局部触发词（来自 应用方式 中的关键词）
    local_triggers = _extract_triggers_from_text(application)

    # 合并触发词
    all_triggers = list(set(global_triggers + local_triggers))[:8]

    # 组装 content
    content_parts = [application]
    if evidence:
        content_parts.append(f"来源: {evidence.strip()}")
    if limitations:
        content_parts.append(f"局限: {limitations.strip()}")

    return {
        "label": name,
        "type": _infer_type(name, core),
        "summary": core[:120],
        "content": "\n".join(content_parts).strip(),
        "triggers": all_triggers,
        "tags": _extract_tags(name, core),
        "_source_evidence": evidence.strip(),
        "_limitations": limitations.strip()
    }


def _infer_type(name: str, core: str) -> str:
    """根据内容推断节点类型。"""
    text = name + core
    if any(kw in text for kw in ["原则", "框架", "定律", "模型", "思维"]):
        return "mental_model"
    if any(kw in text for kw in ["价值观", "信念", "底线", "坚持"]):
        return "value"
    if any(kw in text for kw in ["技巧", "方法", "如何", "操作", "步骤"]):
        return "heuristic"
    if any(kw in text for kw in ["场景", "情境", "故事", "画面", "描写"]):
        return "scene"
    return "concept"


def _extract_triggers_from_text(text: str) -> List[str]:
    """从文本中提取关键词作为触发词。"""
    triggers = []
    # 提取「」中的概念词
    quoted = re.findall(r"「(.+?)」", text)
    triggers.extend(quoted[:5])
    # 提取常见的情感/关系关键词
    emotion_kw = ["爱", "恨", "喜", "怒", "哀", "惧", "悲", "乐", "孤独", "寂寞",
                   "快乐", "痛苦", "愤怒", "恐惧", "厌恶", "惊讶", "好奇"]
    for kw in emotion_kw:
        if kw in text:
            triggers.append(kw)
    return list(set(triggers))[:6]


def _extract_tags(name: str, core: str) -> List[str]:
    """提取标签。"""
    tags = []
    text = name + core
    tag_map = {
        "情感": ["情感", "情绪", "感觉", "心理", "爱", "恨"],
        "人际关系": ["关系", "人际", "社交", "沟通", "交往"],
        "思维方法": ["思维", "认知", "分析", "判断", "推理", "逻辑"],
        "表达风格": ["表达", "语言", "叙事", "描写", "风格", "口吻"],
        "价值判断": ["价值", "选择", "决策", "判断", "取舍"],
        "幽默": ["幽默", "笑话", "吐槽", "嘲讽", "讽刺", "梗"],
    }
    for tag, keywords in tag_map.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)
    return tags[:3]


# ========== CLI 入口 ==========

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python skill_parser.py <path_to_SKILL.md|path_to_skill.json>")
        sys.exit(1)

    filepath = sys.argv[1]
    if filepath.endswith(".json"):
        concepts = parse_skill_json(filepath)
    else:
        concepts = parse_skill_md(filepath)

    for i, c in enumerate(concepts, 1):
        print(f"\n--- Concept {i}: {c['label']} ---")
        print(f"  Type: {c['type']}")
        print(f"  Summary: {c['summary'][:80]}...")
        print(f"  Triggers: {c['triggers']}")
        print(f"  Tags: {c['tags']}")
