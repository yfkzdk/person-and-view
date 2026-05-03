# 高级人物蒸馏系统 - 参考 yourself-skill-master

## 📖 项目价值

**yourself-skill-master** 是一个优秀的人物蒸馏参考项目，核心价值：

### 1. 双层架构设计

```
Part A - Self Memory（自我记忆）
├── 个人经历
├── 核心价值观
├── 生活习惯
├── 重要记忆
├── 人际关系
└── 成长轨迹

Part B - Persona（人格模型）
├── Layer 1: 硬规则层 - 绝对不可违反的规则
├── Layer 2: 身份层 - 基本人份认同
├── Layer 3: 说话风格层 - 语言习惯
├── Layer 4: 情感模式层 - 情绪反应
└── Layer 5: 人际行为层 - 社交模式
```

### 2. 多数据源支持

| 数据源 | 提取内容 | 优势 |
|--------|----------|------|
| 微信聊天记录 | 说话风格、思维模式 | 真实对话数据 |
| QQ聊天记录 | 学生时代的自己 | 时间跨度大 |
| 社交媒体/日记 | 价值观、表达风格 | 深度思考内容 |
| 照片（EXIF） | 时间线、地点 | 构建人生轨迹 |
| 口述/粘贴 | 自我认知 | 主观理解 |

### 3. 核心优势

- ✅ **真实数据驱动**：从实际聊天记录提取
- ✅ **多层性格分析**：5层人格结构深度建模
- ✅ **进化机制**：增量更新、对话纠正
- ✅ **版本管理**：可回滚到历史版本

## 🔧 我们的实现

### 文件：`src/utils/advanced_person_distiller.py`

**核心类**：

1. **SelfMemory** - 自我记忆层
   ```python
   self_memory = SelfMemory()
   self_memory.add_experience("2024-01-01", "开始学习Python", "北京", "开心")
   self_memory.add_memory("我终于搞定了这个项目", "2024-01-03", 0.8)
   ```

2. **PersonaLayer** - 人格层（5层结构）
   ```python
   persona = PersonaLayer()
   persona.identity["name"] = "小明"
   persona.identity["mbti"] = "INTJ"
   persona.speaking_style["catchphrases"] = ["说实话", "其实"]
   ```

3. **AdvancedPersonDistiller** - 高级蒸馏器
   ```python
   distiller = AdvancedPersonDistiller()

   # 从聊天记录蒸馏
   self_memory, persona = distiller.distill_from_chat_history(
       name="小明",
       role="程序员",
       chat_messages=[
           {"time": "2024-01-01", "content": "我决定...", "emotion": "开心"}
       ],
       basic_info={"age": 25, "mbti": "INTJ"}
   )

   # 生成系统提示词
   prompt = distiller.generate_system_prompt(self_memory, persona)
   ```

## 🚀 使用示例

### 示例1：从聊天记录蒸馏

```python
from src.utils.advanced_person_distiller import AdvancedPersonDistiller

# 准备聊天记录
chat_messages = [
    {"time": "2024-01-01", "content": "我决定开始学习Python了", "emotion": "开心"},
    {"time": "2024-01-02", "content": "说实话，这个项目挺难的", "emotion": "困惑"},
    {"time": "2024-01-03", "content": "我终于搞定了！", "emotion": "开心"},
]

# 蒸馏
distiller = AdvancedPersonDistiller()
self_memory, persona = distiller.distill_from_chat_history(
    name="小明",
    role="程序员",
    chat_messages=chat_messages,
    basic_info={"age": 25, "mbti": "INTJ", "zodiac": "摩羯座"}
)

# 生成系统提示词
system_prompt = distiller.generate_system_prompt(self_memory, persona)
print(system_prompt)
```

**输出**：
```
# 自我记忆

## 身份
小明，程序员

MBTI: INTJ
星座: 摩羯座

## 重要记忆
- 我决定开始学习Python了
- 我终于搞定了！

# 人格模型

## 说话风格
口头禅: 说实话, 其实

常用句式:
- 我决定...
- 说实话...

## 情绪反应
- 当感到开心时: 我决定开始学习Python了
- 当感到困惑时: 说实话，这个项目挺难的

## 行为指导
1. 始终保持角色一致性
2. 使用你的口头禅和句式
3. 根据情绪触发点调整回复
4. 引用重要记忆增强真实感
```

### 示例2：集成到对话系统

```python
from src.dialogue.dialogue_manager import DialogueManager
from src.utils.advanced_person_distiller import AdvancedPersonDistiller

# 1. 从聊天记录蒸馏
distiller = AdvancedPersonDistiller()
self_memory, persona = distiller.distill_from_chat_history(
    name="自定义角色",
    role="技术顾问",
    chat_messages=your_chat_messages
)

# 2. 生成系统提示词
system_prompt = distiller.generate_system_prompt(self_memory, persona)

# 3. 创建角色卡片
from src.models.character_card import CharacterCard

card = CharacterCard(
    name="自定义角色",
    description="从真实聊天记录蒸馏的角色",
    system_prompt=system_prompt,
    custom_fields={
        "self_memory": self_memory.to_dict(),
        "persona": persona.to_dict()
    }
)

# 4. 使用对话系统
dialogue = DialogueManager(character_name="自定义角色")
```

## 📊 对比：基础蒸馏 vs 高级蒸馏

| 特性 | 基础蒸馏 | 高级蒸馏（参考 yourself-skill） |
|------|----------|--------------------------------|
| 数据源 | 对话样本 | 聊天记录、日记、照片、口述 |
| 架构 | 单层 | 双层（Self Memory + Persona） |
| 人格深度 | 3层 | 5层 |
| 记忆系统 | 无 | 重要记忆、成长轨迹 |
| 情绪分析 | 关键词匹配 | 情绪触发点、应对机制 |
| 说话风格 | 口头禅 | 句式、语气、填充词 |
| 进化机制 | 无 | 增量更新、对话纠正 |
| 版本管理 | 无 | 可回滚 |

## 🎯 最佳实践

### 1. 数据收集建议

**优先提供**：
- ✅ 深夜对话/独白 - 最能暴露真实性格
- ✅ 情绪波动的记录 - 生气、难过、兴奋时的表达
- ✅ 做决定的聊天记录 - 暴露决策模式
- ✅ 日常闲扯 - 提炼口头禅和语气词

**数据质量**：
```
聊天记录 + 日记/笔记 > 仅口述
```

### 2. 蒸馏流程

```
Step 1: 收集数据
  ├── 微信聊天记录导出（WeChatMsg/PyWxDump）
  ├── QQ聊天记录导出
  ├── 社交媒体截图/日记
  └── 照片（含EXIF信息）

Step 2: 分析数据
  ├── 提取说话风格（口头禅、句式）
  ├── 提取情绪模式（触发点、反应）
  ├── 提取重要事件（决策、转折点）
  └── 构建时间线（成长轨迹）

Step 3: 生成双层结构
  ├── Self Memory（记忆层）
  └── Persona（人格层）

Step 4: 生成系统提示词
  └── 整合双层结构
  └── 添加行为指导

Step 5: 验证和迭代
  ├── 测试对话效果
  ├── 对话纠正
  └── 版本更新
```

### 3. 进化机制

**增量更新**：
```python
# 找到新的聊天记录
new_messages = [...]

# 增量分析
distiller.update_from_new_messages(new_messages)

# 自动merge进现有结构
```

**对话纠正**：
```python
# 用户说："我不会这样说"
# 系统写入 Correction 层，立即生效
```

## 🔗 参考项目

- **yourself-skill-master**: https://github.com/notdog1998/yourself-skill
- **同事.skill**: https://github.com/titanwings/colleague-skill
- **前任.skill**: https://github.com/therealXiaomanChu/ex-partner-skill

## 📝 总结

**yourself-skill-master** 项目非常适合作为人物语言逻辑蒸馏的参考！

**核心价值**：
1. ✅ 双层架构设计（Self Memory + Persona）
2. ✅ 多数据源支持（聊天记录、日记、照片）
3. ✅ 5层人格结构深度建模
4. ✅ 进化机制（增量更新、纠正）
5. ✅ 真实数据驱动

**我们的实现**：
- ✅ 已创建 `AdvancedPersonDistiller`
- ✅ 支持 SelfMemory 和 PersonaLayer
- ✅ 可从聊天记录蒸馏
- ✅ 生成完整系统提示词
- ✅ 可集成到对话系统

---

**现在您可以使用高级蒸馏功能，从真实聊天记录创建更真实的人物模拟！**