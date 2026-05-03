# 人物模拟系统使用指南

## 📖 系统概述

本系统实现了完整的AI人物模拟功能，参考了GitHub上多个成熟开源项目的最佳实践：

- **SillyTavern** - 角色卡片系统
- **Smart-Memory** - 多层级记忆架构
- **Character-LLM** - 角色扮演训练方法

## 🎯 核心功能

### 1. 角色卡片系统

**文件**: `src/models/character_card.py`

**功能**:
- 创建和管理角色卡片
- 兼容SillyTavern格式
- 导入/导出角色卡片
- 自动生成系统提示词

**使用示例**:
```python
from src.models.character_card import CharacterCardManager

# 创建管理器
manager = CharacterCardManager()
manager.create_default_characters()

# 获取角色
xiaoyun = manager.get_card("小云")

# 生成系统提示词
system_prompt = xiaoyun.to_system_prompt()

# 导出角色卡片
xiaoyun.export_to_file("characters/xiaoyun.json")
```

### 2. 记忆系统

**文件**: `src/memory/smart_memory.py`

**功能**:
- **短期记忆**: 最近N轮对话
- **长期记忆**: 重要事实和偏好
- **情节记忆**: 故事线追踪
- **自动摘要**: 提取关键信息

**使用示例**:
```python
from src.memory.smart_memory import SmartMemorySystem

# 创建记忆系统
memory = SmartMemorySystem(max_short_term_turns=10)

# 记录交互
memory.process_interaction(
    user_input="我喜欢打篮球",
    assistant_response="太好了！篮球是一项很棒的运动。"
)

# 获取相关上下文
context = memory.get_relevant_context("我想运动")
```

### 3. 情绪感知系统

**文件**: `src/emotion/emotion_aware_dialogue.py`

**功能**:
- 实时检测用户情绪
- 根据情绪调整回复策略
- 结合角色特征生成情绪化回复

**使用示例**:
```python
from src.emotion.emotion_aware_dialogue import EmotionAwareResponder

# 创建情绪感知回复器
responder = EmotionAwareResponder(character_card)

# 分析情绪
emotion_state = responder.analyze_user_emotion("我最近很焦虑")
print(f"检测到情绪: {emotion_state.primary_emotion}")

# 生成情绪感知提示词
prompt = responder.get_emotion_aware_prompt(user_input, emotion_state)
```

### 4. 角色蒸馏

**文件**: `src/utils/person_distiller.py`

**功能**:
- 从对话样本中提取人物特征
- 自动分析性格特质
- 识别说话风格
- 提取口头禅

**使用示例**:
```python
from src.utils.person_distiller import PersonDistiller

# 准备对话样本
dialogues = [
    ("我遇到一个问题", "让我来帮你分析一下..."),
    ("这个方案可行吗？", "从实际角度来看..."),
]

# 蒸馏角色
distiller = PersonDistiller()
profile = distiller.distill_from_dialogues(
    name="分析师",
    role="技术顾问",
    dialogues=dialogues
)

# 保存
distiller.save_profile(profile, "analyst_profile.json")
```

### 5. 角色管理API

**文件**: `src/api/character_routes.py`

**API端点**:

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/characters/` | GET | 列出所有角色 |
| `/api/characters/{name}` | GET | 获取角色详情 |
| `/api/characters/` | POST | 创建新角色 |
| `/api/characters/{name}` | PUT | 更新角色 |
| `/api/characters/{name}` | DELETE | 删除角色 |
| `/api/characters/{name}/activate` | POST | 激活角色 |
| `/api/characters/distill` | POST | 蒸馏角色 |
| `/api/characters/import` | POST | 导入角色卡片 |
| `/api/characters/export/{name}` | POST | 导出角色卡片 |

**集成到FastAPI**:
```python
from fastapi import FastAPI
from src.api.character_routes import setup_character_routes

app = FastAPI()
setup_character_routes(app)
```

## 🚀 快速开始

### 1. 测试完整系统

```bash
cd O:\AII\app\voices
python test_complete_person_system.py
```

### 2. 在现有系统中使用

```python
from src.models.character_card import CharacterCardManager
from src.memory.smart_memory import SmartMemorySystem
from src.emotion.emotion_aware_dialogue import EmotionAwareResponder
from src.llm.llm_router import LLMRouter

# 1. 加载角色
manager = CharacterCardManager()
manager.create_default_characters()
character = manager.get_card("小云")

# 2. 初始化系统
memory = SmartMemorySystem()
emotion_responder = EmotionAwareResponder(character)
llm_router = LLMRouter(config, context_manager)
llm_router.set_person_profile(character)

# 3. 处理用户输入
user_input = "我最近感觉很焦虑"

# 情绪分析
emotion = emotion_responder.analyze_user_emotion(user_input)

# 获取记忆上下文
context = memory.get_relevant_context(user_input)

# 生成回复
response = await llm_router.chat(user_input)

# 存入记忆
memory.process_interaction(user_input, response)
```

## 📊 系统架构

```
用户输入
    ↓
[情绪分析] → 检测情绪状态
    ↓
[记忆检索] → 获取相关上下文
    ↓
[角色系统] → 应用角色特征
    ↓
[LLM生成] → 生成回复
    ↓
[记忆存储] → 保存对话
    ↓
输出回复
```

## 🎭 预置角色

### 1. 小云 - 心理咨询师
- **性格**: 温暖、同理心强、专业
- **特点**: 善于倾听和共情
- **适用场景**: 心理咨询、情感支持

### 2. 小明 - 幽默朋友
- **性格**: 幽默、乐观、讲义气
- **特点**: 喜欢开玩笑，关键时刻靠谱
- **适用场景**: 日常聊天、娱乐

### 3. 分析师 - 理性顾问
- **性格**: 理性、严谨、善于分析
- **特点**: 逻辑清晰，客观专业
- **适用场景**: 问题分析、决策支持

## 🔧 自定义角色

### 方法1: 手动创建

```python
manager.create_card(
    name="自定义角色",
    description="角色描述",
    personality="性格特点",
    custom_fields={
        "emotional_responses": {
            "焦虑": "安抚情绪，提供支持"
        },
        "expertise_areas": ["专业领域"],
        "catchphrases": ["口头禅"]
    }
)
```

### 方法2: 从对话蒸馏

```python
dialogues = [
    ("用户输入1", "角色回复1"),
    ("用户输入2", "角色回复2"),
]

profile = distiller.distill_from_dialogues(
    name="新角色",
    role="角色定位",
    dialogues=dialogues
)
```

## 📁 文件结构

```
O:\AII\app\voices\
├── src/
│   ├── models/
│   │   ├── character_card.py      # 角色卡片系统
│   │   └── person_profile.py      # 人物档案模型
│   ├── memory/
│   │   └── smart_memory.py        # 智能记忆系统
│   ├── emotion/
│   │   └── emotion_aware_dialogue.py  # 情绪感知对话
│   ├── utils/
│   │   └── person_distiller.py    # 角色蒸馏器
│   └── api/
│       └── character_routes.py    # 角色管理API
├── characters/                    # 角色卡片存储
│   ├── 小云.json
│   ├── 小明.json
│   └── 分析师.json
├── memory/                        # 记忆数据存储
│   └── long_term.json
└── test_complete_person_system.py # 完整测试脚本
```

## 🎯 最佳实践

### 1. 角色设计
- 明确角色的核心特征
- 提供足够的对话示例
- 定义情绪反应模式

### 2. 记忆管理
- 定期清理短期记忆
- 提取重要信息到长期记忆
- 使用故事线追踪连续对话

### 3. 情绪感知
- 根据情绪强度调整回复
- 对负面情绪给予更多关注
- 结合角色特征表达情绪

## 🔗 参考项目

- [SillyTavern](https://github.com/SillyTavern/SillyTavern) - 角色卡片格式
- [Smart-Memory](https://github.com/senjinthedragon/Smart-Memory) - 记忆系统架构
- [Character-LLM](https://github.com/choosewhatulike/trainable-agents) - 角色扮演训练

## 📝 更新日志

**v1.0.0** (2026-04-27)
- ✅ 实现角色卡片系统
- ✅ 实现多层级记忆系统
- ✅ 实现情绪感知对话
- ✅ 实现角色蒸馏功能
- ✅ 提供完整的REST API
- ✅ 创建预置角色库

---

**系统已完全实现，无需克隆任何GitHub项目！** 所有功能都已集成到您的现有系统中。
