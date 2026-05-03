# 细粒度情绪识别系统

## 概述

基于Plutchik情绪轮和PAD维度模型的细粒度情绪识别系统，支持70+种情绪类型，提供更精细、更全面的情绪分析能力。

## 核心特性

### 1. 70+细粒度情绪类型

基于Plutchik情绪轮理论，包含：

**8个基础情绪家族：**
- **Joy (喜悦)**: Serenity, Joy, Happiness, Cheerfulness, Delight, Enthusiasm, Euphoria, Ecstasy, Bliss
- **Trust (信任)**: Acceptance, Trust, Admiration, Respect, Confidence, Devotion, Reverence, Faith
- **Fear (恐惧)**: Apprehension, Anxiety, Fear, Worry, Uneasiness, Dread, Terror, Panic, Horror
- **Surprise (惊讶)**: Surprise, Astonishment, Amazement, Wonder, Shock, Stun, Astoundment
- **Sadness (悲伤)**: Pensiveness, Melancholy, Sadness, Gloom, Disappointment, Grief, Despair, Sorrow, Depression
- **Disgust (厌恶)**: Boredom, Indifference, Disgust, Aversion, Distaste, Loathing, Revulsion, Hatred, Abhorrence
- **Anger (愤怒)**: Annoyance, Irritation, Frustration, Anger, Resentment, Rage, Fury, Wrath, Outrage
- **Anticipation (期待)**: Interest, Curiosity, Anticipation, Expectation, Hope, Vigilance, Eagerness, Excitement

**二元情绪（情绪组合）：**
- **Love (爱)** = Joy + Trust: Affection, Fondness, Adoration
- **Optimism (乐观)** = Joy + Anticipation: Hopefulness, Enthusiasm
- **Submission (顺从)** = Trust + Fear: Compliance, Resignation
- **Awe (敬畏)** = Fear + Surprise: Wonder
- **Disappointment (失望)** = Surprise + Sadness: Dismay, Dismayement
- **Remorse (懊悔)** = Sadness + Disgust: Guilt, Shame, Regret
- **Contempt (蔑视)** = Disgust + Anger: Scorn, Disdain
- **Aggressiveness (攻击性)** = Anger + Anticipation: Hostility

**扩展细微情绪：**
- Nostalgia, Longing, Yearning (思念类)
- Relief, Contentment, Gratitude (满足类)
- Embarrassment, Shyness, Self-consciousness (尴尬类)
- Confusion, Perplexity (困惑类)
- Sympathy, Compassion, Empathy (同情类)
- Pride, Triumph, Satisfaction (自豪类)
- Envy, Jealousy (嫉妒类)
- Seriousness, Determination (决心类)

### 2. PAD三维情绪维度

基于Mehrabian的PAD模型，每种情绪映射到三维连续空间：

| 维度 | 范围 | 描述 |
|------|------|------|
| **Pleasure (愉悦度)** | -1 到 1 | 负值表示不愉悦，正值表示愉悦 |
| **Arousal (唤醒度)** | -1 到 1 | 负值表示平静，正值表示兴奋 |
| **Dominance (支配度)** | -1 到 1 | 负值表示被支配，正值表示支配 |

**典型情绪的PAD值：**
- Joy: P=0.7, A=0.5, D=0.3 (高愉悦、中等唤醒)
- Anger: P=-0.6, A=0.7, D=0.6 (低愉悦、高唤醒、高支配)
- Fear: P=-0.6, A=0.6, D=-0.5 (低愉悦、高唤醒、低支配)
- Sadness: P=-0.7, A=-0.4, D=-0.4 (低愉悦、低唤醒、低支配)

### 3. 情绪强度量化

- **强度等级**: 1-3级（低、中、高）
- **连续强度值**: 0.0-1.0
- **强度词识别**: 自动识别"非常"、"有点"等强度修饰词

## 使用方法

### 基础用法

```python
from src.emotion.fine_grained_emotion import FineGrainedEmotionAnalyzer

# 初始化分析器
analyzer = FineGrainedEmotionAnalyzer()

# 分析文本情绪
result = analyzer.analyze("我今天太开心了！")

print(f"主要情绪: {result.primary_emotion.value}")      # 喜悦
print(f"情绪家族: {result.primary_emotion.family}")    # joy
print(f"强度等级: {result.primary_emotion.intensity_level}")  # 1-3
print(f"强度值: {result.intensity}")                   # 0.0-1.0
print(f"置信度: {result.confidence}")                  # 0.0-1.0
print(f"PAD维度: {result.pad_dimensions.to_dict()}")   # {pleasure, arousal, dominance}
```

### 情绪类型查询

```python
from src.emotion.fine_grained_emotion import FineEmotionType

# 获取所有情绪类型
all_emotions = list(FineEmotionType)
print(f"支持 {len(all_emotions)} 种情绪")

# 查询特定情绪的属性
joy = FineEmotionType.JOY
print(f"中文标签: {joy.value}")           # 喜悦
print(f"情绪家族: {joy.family}")          # joy
print(f"强度等级: {joy.intensity_level}") # 1

# 查询情绪的PAD维度
joy_pad = joy.to_pad()
print(f"愉悦度: {joy_pad.pleasure}")   # 0.7
print(f"唤醒度: {joy_pad.arousal}")    # 0.5
print(f"支配度: {joy_pad.dominance}")  # 0.3
```

### 次要情绪分析

```python
# 分析包含多种情绪的文本
result = analyzer.analyze("我很开心，但也有点担心")

if result.secondary_emotions:
    for emotion, prob in result.secondary_emotions.items():
        print(f"次要情绪: {emotion.value}, 概率: {prob:.2f}")
```

### PAD维度模型

```python
from src.emotion.emotion_dimensions import EmotionDimension

# 创建PAD维度
pad = EmotionDimension(pleasure=0.5, arousal=0.3, dominance=0.2)

print(f"愉悦度: {pad.pleasure}")
print(f"唤醒度: {pad.arousal}")
print(f"支配度: {pad.dominance}")

# 转换为字典
pad_dict = pad.to_dict()
```

### 与现有系统集成

```python
from src.emotion.fine_grained_emotion import FineGrainedEmotionAnalyzer
from src.emotion.enterprise_emotion import TextEmotionAnalyzer

# 细粒度分析器
fine_analyzer = FineGrainedEmotionAnalyzer()

# 现有分析器
basic_analyzer = TextEmotionAnalyzer()

text = "我感到非常愤怒"

# 细粒度分析
fine_result = fine_analyzer.analyze(text)
print(f"细粒度情绪: {fine_result.primary_emotion.value}")  # 愤怒
print(f"情绪家族: {fine_result.primary_emotion.family}")  # anger

# 基础分析
basic_result = basic_analyzer.analyze(text)
print(f"基础情绪: {basic_result.type}")  # anger
```

## 数据结构

### FineEmotionType

```python
class FineEmotionType(Enum):
    """
    细粒度情绪类型枚举

    属性:
        value: 中文标签
        family: 情绪家族 (joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
        intensity_level: 强度等级 (1-3)
    """
    JOY = ("喜悦", "joy", 1)
    ECSTASY = ("狂喜", "joy", 3)
    # ... 70+ 种情绪
```

### RichEmotionState

```python
@dataclass
class RichEmotionState:
    """丰富的情绪状态表示"""
    primary_emotion: FineEmotionType           # 主要情绪类型
    intensity: float                           # 情绪强度 (0.0-1.0)
    confidence: float                          # 识别置信度 (0.0-1.0)
    pad_dimensions: EmotionDimension           # PAD三维情绪维度
    secondary_emotions: Optional[Dict[FineEmotionType, float]] = None  # 次要情绪
```

### EmotionDimension

```python
@dataclass
class EmotionDimension:
    """PAD三维情绪维度模型"""
    pleasure: float    # 愉悦度 (-1.0 到 1.0)
    arousal: float     # 唤醒度 (-1.0 到 1.0)
    dominance: float   # 支配度 (-1.0 到 1.0)
```

## 技术实现

### 模型架构

```
Chinese-BERT-wwm (hfl/chinese-roberta-wwm-ext)
    │
    ├─> Emotion Classifier (768 → 512 → 256 → 70+)
    │       3层全连接网络，输出70+种情绪分类
    │
    └─> Intensity Regressor (768 → 256 → 1)
            2层全连接网络，输出强度值 (0.0-1.0)
```

### Fallback机制

当BERT模型不可用时，自动切换到关键词匹配模式：

- **关键词映射**: 预定义情绪关键词词典
- **强度识别**: 基于"非常"、"有点"等修饰词
- **置信度调整**: fallback模式置信度降低

```python
# Fallback模式自动启用
analyzer = FineGrainedEmotionAnalyzer()
# 如果BERT加载失败，自动使用关键词匹配
```

### 情绪关键词映射

```python
EMOTION_KEYWORDS = {
    'JOY': ['开心', '高兴', '快乐', '喜悦'],
    'ECSTASY': ['狂喜', '欣喜若狂', '太棒了'],
    'SADNESS': ['悲伤', '难过', '伤心', '失落'],
    'ANGER': ['愤怒', '生气', '恼火'],
    # ... 更多映射
}
```

## 性能指标

| 指标 | BERT模式 | Fallback模式 |
|------|----------|--------------|
| 情绪类型 | 70+ 种 | 70+ 种 |
| 识别延迟 | ~100ms | <10ms |
| 准确率 | 85%+ | 60-70% |
| 强度识别 | 连续值 | 离散级别 |

## 测试

运行测试：

```bash
python -m pytest tests/emotion/test_fine_grained_emotion.py -v
```

测试覆盖：

- 情绪维度创建和验证
- 细粒度情绪类型枚举
- PAD维度映射
- RichEmotionState创建和验证
- 情绪分析器初始化和分析
- 强度识别
- 空输入处理
- 与现有检测器集成

## 应用场景

1. **情感对话系统** - 精细识别用户情绪，提供更自然的响应
2. **心理健康监测** - 追踪情绪变化趋势，识别异常情绪状态
3. **内容情感分析** - 分析文章、评论的情感倾向和强度
4. **智能客服** - 实时检测客户情绪，调整服务策略
5. **教育辅导** - 根据学生情绪状态调整教学方式

## 与企业版情绪系统对比

| 特性 | 细粒度系统 | 企业版系统 |
|------|-----------|-----------|
| 情绪类型 | 70+ 种 | 7 种 |
| 维度模型 | PAD三维 | 无 |
| 强度等级 | 3级 + 连续值 | 连续值 |
| 情绪家族 | 8个基础 + 二元组合 | 6种基础 |
| 适用场景 | 精细分析 | 快速检测 |

## 扩展性

- **自定义情绪类型**: 可扩展FineEmotionType枚举
- **多语言支持**: 可替换BERT模型支持其他语言
- **实时处理**: 支持流式文本分析
- **模型微调**: 支持在特定领域数据上微调

## 参考文献

- Plutchik, R. (1980). A general psychoevolutionary theory of emotion. In *Emotion: Theory, research, and experience* (Vol. 1, pp. 3-33).
- Mehrabian, A. (1996). Pleasure-arousal-dominance: A general framework for describing and measuring individual differences in temperament. *Current Psychology*, 14(4), 261-292.
- Cowen, A. S., & Keltner, D. (2017). Self-report captures 27 distinct categories of emotion bridged by continuous gradients. *Proceedings of the National Academy of Sciences*, 114(38), E7900-E7909.
