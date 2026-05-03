# 深度学习画像引擎

## 概述

企业级深度学习用户画像引擎，实现个性化声音、语言风格和交互模式的智能预测。

## 核心组件

### 1. DeepUserProfiler - 深度学习画像引擎

**功能**：
- 多模态编码（文本、音频、行为）
- 用户画像向量生成
- 偏好预测（声音、语言、交互）

**使用示例**：
```python
from src.personalization.deep_profiler import DeepUserProfiler

# 初始化
profiler = DeepUserProfiler()

# 生成画像
text_history = ["你好", "我喜欢听故事"]
profile = profiler(text_history, "user-123")

# 查看偏好
print(f"语速: {profile.voice_preferences.speed}")
print(f"正式度: {profile.language_preferences.formality}")
print(f"偏好角色: {profile.interaction_preferences.preferred_role}")
```

### 2. UserProfileManager - 用户画像管理器

**功能**：
- 画像持久化存储
- 在线学习更新
- 画像版本管理

**使用示例**：
```python
from src.personalization.profile_manager import UserProfileManager
from src.personalization.deep_profiler import DeepUserProfiler

# 初始化
profiler = DeepUserProfiler()
manager = UserProfileManager(profiler)

# 获取画像
profile = await manager.get_profile("user-123")

# 更新画像
updated = await manager.update_profile(
    "user-123",
    "新的交互文本",
    learning_rate=0.1
)
```

## 架构设计

```
用户输入
    ↓
文本编码器 (BERT)
    ↓
画像生成网络 (MLP)
    ↓
偏好预测网络
    ├── 声音偏好 (VoicePreferenceNetwork)
    ├── 语言风格 (LanguageStyleNetwork)
    └── 交互模式 (InteractionPatternNetwork)
    ↓
用户画像 (DeepUserProfile)
```

## 网络结构

### VoicePreferenceNetwork
- 输入: 256维画像向量
- 输出:
  - 音色混合权重 (10维)
  - 语速 (0.5-2.0)
  - 音调 (-50到50)
  - 情感强度 (8维)

### LanguageStyleNetwork
- 输入: 256维画像向量
- 输出:
  - 正式度 (0-1)
  - 幽默度 (0-1)
  - 细节度 (0-1)
  - 情感表达 (0-1)

### InteractionPatternNetwork
- 输入: 256维画像向量
- 输出:
  - 响应长度偏好 (0-1)
  - 偏好角色 (5种)
  - 情感敏感度 (0-1)

## 在线学习

支持增量更新用户画像：

```python
# 初始画像
profile = profiler(["初始文本"], "user-123")

# 在线更新
updated_profile = profiler.update_profile(
    profile,
    "新的交互",
    learning_rate=0.1  # 学习率
)
```

**更新策略**：指数移动平均 (EMA)
```
new_embedding = (1 - α) * old_embedding + α * new_features
```

## 存储格式

画像以JSON格式存储在 `data/profiles/` 目录：

```json
{
  "user_id": "user-123",
  "embedding": [[...]],  // 256维向量
  "voice_preferences": {
    "timbre_weights": [[...]],
    "speed": 1.2,
    "pitch": 5.0,
    "emotion_intensities": [[...]]
  },
  "language_preferences": {
    "formality": 0.7,
    "humor": 0.5,
    "detail": 0.8,
    "emotion_expression": 0.6
  },
  "interaction_preferences": {
    "response_length": 0.6,
    "preferred_role": "storyteller",
    "emotional_sensitivity": 0.7
  },
  "confidence": 0.85,
  "version": 3,
  "created_at": "2026-04-26T05:00:00",
  "updated_at": "2026-04-26T05:05:00"
}
```

## 性能指标

- **画像生成延迟**: < 100ms
- **在线更新延迟**: < 50ms
- **存储大小**: ~10KB per profile
- **内存占用**: ~5MB (1000 profiles)

## 扩展性

### 添加新的偏好维度

1. 创建新的偏好网络：
```python
class NewPreferenceNetwork(nn.Module):
    def __init__(self, input_dim=256):
        super().__init__()
        self.network = nn.Sequential(...)
    
    def forward(self, profile_embedding):
        # 返回新偏好
        pass
```

2. 集成到 DeepUserProfiler：
```python
self.new_predictor = NewPreferenceNetwork()
```

### 支持新的模态

1. 添加编码器：
```python
self.video_encoder = VideoEncoder()
```

2. 融合多模态特征：
```python
fused = torch.cat([text_emb, video_emb], dim=-1)
```

## 测试

运行测试：
```bash
pytest tests/personalization/test_deep_profiler.py -v
```

## 下一步

- [ ] 集成音频编码器 (Wav2Vec2)
- [ ] 实现画像聚类分析
- [ ] 添加画像可视化工具
- [ ] 优化在线学习算法

## 参考

- BERT: https://arxiv.org/abs/1810.04805
- User Modeling: https://dl.acm.org/doi/10.1145/2955103