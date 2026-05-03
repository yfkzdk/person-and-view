# 多角色协同系统

## 概述

企业级多角色协同系统，实现智能角色选择、角色协调和角色转换。

## 核心组件

### 1. RoleSkills - 角色定义库

**预定义角色**：
- **storyteller** - 故事讲述者：温暖生动，富有感染力
- **mentor** - 智慧导师：循循善诱，启发思考
- **companion** - 贴心伙伴：轻松活泼，善解人意
- **expert** - 专业专家：严谨专业，深度分析
- **friend** - 亲密朋友：真诚自然，情感共鸣

**角色属性**：
- 声音配置（音色、语速、音调、风格）
- 语言模板（风格、特点、表达方式）
- 情绪映射（不同情绪的响应方式）
- 特质标签（性格特点）
- 专长领域（专业能力）

### 2. MultiRoleSystem - 多角色协同系统

**核心功能**：
- 智能角色选择
- 多角色协调生成
- 角色转换规划

**使用示例**：
```python
from src.skills.multi_role_system import MultiRoleSystem
from src.personalization.deep_profiler import DeepUserProfile

# 初始化
system = MultiRoleSystem()

# 处理用户输入
response = await system.process_with_roles(
    "请讲一个关于科学的故事",
    user_profile
)

# 查看响应
print(f"内容: {response.content}")
print(f"角色: {[r.name for r in response.roles]}")
```

### 3. RoleManager - 角色管理器

**功能**：
- 主角色选择
- 辅助角色选择
- 角色匹配分析

**选择策略**：
1. 明确指定检测（关键词匹配）
2. 用户画像偏好（preferred_role）
3. 内容分析（NLP分析）
4. 默认角色（companion）

### 4. RoleCoordinator - 角色协调器

**功能**：
- 多角色协同生成
- 响应融合
- 角色贡献分配

**协调流程**：
```
主角色生成主体内容
    ↓
辅助角色补充观点
    ↓
融合多个响应
    ↓
生成最终响应
```

### 5. RoleTransitionEngine - 角色转换引擎

**功能**：
- 转换需求分析
- 目标角色选择
- 转换风格设计

**转换风格**：
- **HANDOFF** - 直接交接："让我换个角度来回答你..."
- **COLLABORATION** - 协作过渡："我想请我的朋友来补充一下..."
- **EVOLUTION** - 自然演变："现在让我用另一种方式来说..."

## 架构设计

```
用户输入 + 用户画像
    ↓
RoleManager
    ├── 主角色选择
    └── 辅助角色选择
    ↓
RoleCoordinator
    ├── 主角色生成
    ├── 辅助角色补充
    └── 响应融合
    ↓
RoleTransitionEngine
    └── 角色转换规划
    ↓
MultiRoleResponse
```

## 角色定义示例

```python
RoleSkill(
    id="storyteller",
    name="故事讲述者",
    description="温暖的故事讲述者，擅长用生动的语言创造画面感",
    voice_config=VoiceConfig(
        base_voice="XiaoxiaoNeural",
        rate=0.95,
        pitch=5,
        style="narration-relaxed"
    ),
    language_template="你是一位温暖的故事讲述者...",
    emotion_mapping={
        "joy": "cheerful",
        "sadness": "empathetic"
    },
    traits=["温暖", "生动", "富有感染力"],
    expertise=["故事创作", "情感表达"]
)
```

## 角色选择逻辑

### 主角色选择

```python
# 1. 明确指定
if "讲故事" in user_input:
    return "storyteller"

# 2. 用户画像
if user_profile.preferred_role:
    return user_profile.preferred_role

# 3. 内容分析
if "为什么" in user_input:
    return "mentor"

# 4. 默认
return "companion"
```

### 辅助角色选择

```python
# 需要专业知识
if needs_expertise(user_input):
    supporting.append("expert")

# 需要情感支持
if needs_emotional_support(user_input):
    supporting.append("companion")

# 需要教学引导
if needs_teaching(user_input):
    supporting.append("mentor")
```

## 多角色协同示例

**场景**：用户问"请讲一个关于科学的故事"

**角色分配**：
- 主角色：storyteller（故事讲述）
- 辅助角色：expert（科学知识）

**响应生成**：
```
[故事讲述者] 很久以前，在一个遥远的实验室里...

[专业专家] 从科学角度来看，这个故事展示了...

[融合响应] 完整的故事 + 科学解释
```

## 角色转换示例

**场景**：从轻松聊天转为专业咨询

**转换流程**：
```
检测转换需求
    ↓
选择目标角色（companion → expert）
    ↓
设计转换风格（EVOLUTION）
    ↓
生成转换文本："现在让我用另一种方式来说..."
    ↓
平滑过渡到新角色
```

## 性能指标

- **角色选择延迟**: < 50ms
- **多角色协调延迟**: < 200ms
- **角色转换延迟**: < 100ms
- **支持角色数**: 5个（可扩展）

## 扩展性

### 添加新角色

```python
# 1. 定义角色
new_role = RoleSkill(
    id="coach",
    name="教练",
    description="激励型教练，帮助用户达成目标",
    voice_config=VoiceConfig(...),
    language_template="...",
    emotion_mapping={...},
    traits=["激励", "目标导向"],
    expertise=["目标设定", "行动计划"]
)

# 2. 注册角色
ROLE_SKILLS["coach"] = new_role
```

### 自定义角色选择策略

```python
class CustomRoleManager(RoleManager):
    async def select_primary_role(self, user_input, profile, context):
        # 自定义逻辑
        return custom_selected_role
```

## 测试

运行测试：
```bash
pytest tests/skills/test_multi_role_system.py -v
```

## 下一步

- [ ] 集成LLM生成真实响应
- [ ] 实现角色音频生成
- [ ] 添加角色可视化
- [ ] 优化角色转换算法

## 参考

- Multi-Agent Systems: https://arxiv.org/abs/2006.02939
- Role-Based Dialogue: https://aclanthology.org/2020.acl-main.92/