# 🎯 实时语音叙事系统 - 深度定制方案设计文档

## 核心需求分析

### 需求1：个性化声音与语言逻辑专项化
- 每个用户独立的声音角色
- 基于 Skill 的角色定制系统
- 语言风格个性化适配

### 需求2：前端交互体验优化
- 亲切友好的界面设计
- 实时音频波动可视化
- 情感反馈动画效果

### 需求3：用户情绪感知与行为推理
- 实时情绪检测
- 用户行为模式分析
- 智能响应策略调整

---

# 📋 方案一：轻量级快速实现方案

## 设计理念
**"快速落地，渐进优化"** - 使用轻量级技术栈，快速实现核心功能，后续逐步增强

---

## 一、个性化声音与语言系统

### 1.1 架构设计

```
用户画像系统
    ↓
角色 Skill 选择器
    ↓
声音配置 + 语言模板
    ↓
个性化生成
```

### 1.2 核心组件

#### A. 用户画像管理
```python
# src/personalization/user_profile.py

class UserProfile:
    """用户画像"""
    user_id: str
    voice_preference: str  # "warm", "professional", "playful"
    language_style: str    # "casual", "formal", "narrative"
    personality_traits: Dict[str, float]  # {幽默: 0.8, 严谨: 0.3}

    # 历史偏好学习
    interaction_history: List[Interaction]
    preferred_skills: List[str]
```

#### B. 角色 Skill 系统
```python
# src/skills/role_skills.py

ROLE_SKILLS = {
    "storyteller": {
        "name": "故事讲述者",
        "voice": {
            "base": "XiaoxiaoNeural",
            "rate": 0.95,
            "pitch": 5,
            "style": "narration-relaxed"
        },
        "language_template": """
            你是一位温暖的故事讲述者。
            风格：娓娓道来，富有画面感
            特点：使用生动的比喻，自然的停顿
            标记：[pause] 表示停顿，[slow] 表示放慢
        """,
        "emotion_mapping": {
            "joy": "cheerful",
            "sadness": "empathetic",
            "neutral": "calm"
        }
    },

    "mentor": {
        "name": "智慧导师",
        "voice": {
            "base": "YunxiNeural",
            "rate": 0.85,
            "pitch": -5,
            "style": "serious"
        },
        "language_template": """
            你是一位睿智的导师。
            风格：循循善诱，启发思考
            特点：提问式引导，逻辑清晰
        """,
        "emotion_mapping": {
            "joy": "encouraging",
            "confusion": "patient",
            "neutral": "thoughtful"
        }
    },

    "companion": {
        "name": "贴心伙伴",
        "voice": {
            "base": "XiaoyiNeural",
            "rate": 1.05,
            "pitch": 10,
            "style": "friendly"
        },
        "language_template": """
            你是一位贴心的伙伴。
            风格：轻松活泼，善解人意
            特点：共情回应，幽默调节
        """,
        "emotion_mapping": {
            "joy": "excited",
            "sadness": "comforting",
            "neutral": "friendly"
        }
    }
}
```

#### C. 动态角色切换
```python
# src/personalization/role_selector.py

class RoleSelector:
    """智能角色选择器"""

    def select_role(self, user_input: str, user_profile: UserProfile) -> str:
        """根据用户输入和画像选择最合适的角色"""

        # 1. 检查用户明确指定
        if "讲故事" in user_input or "说说" in user_input:
            return "storyteller"

        if "教我" in user_input or "怎么" in user_input:
            return "mentor"

        # 2. 基于用户画像偏好
        if user_profile.preferred_skills:
            return user_profile.preferred_skills[0]

        # 3. 基于历史交互模式
        interaction_pattern = self._analyze_pattern(user_profile.interaction_history)
        return self._pattern_to_role(interaction_pattern)

        # 4. 默认角色
        return "companion"
```

### 1.3 实现步骤

**步骤1**：创建角色 Skill 定义文件
```bash
创建：src/skills/role_skills.py
定义：3-5个核心角色（故事讲述者、导师、伙伴等）
```

**步骤2**：实现用户画像系统
```bash
创建：src/personalization/user_profile.py
功能：用户偏好存储、历史学习、画像更新
```

**步骤3**：集成到现有系统
```python
# 修改 src/llm/llm_router.py

async def chat(self, user_input: str, user_id: str):
    # 1. 加载用户画像
    profile = await self.profile_manager.get_profile(user_id)

    # 2. 选择角色
    role = self.role_selector.select_role(user_input, profile)

    # 3. 加载角色 Skill
    skill = ROLE_SKILLS[role]

    # 4. 应用声音配置
    voice_config = skill["voice"]

    # 5. 应用语言模板
    system_prompt = skill["language_template"]

    # 6. 生成响应
    response = await self._generate(user_input, system_prompt)

    # 7. TTS 使用角色声音
    audio = await self._synthesize(response, voice_config)

    return audio
```

---

## 二、前端交互体验优化

### 2.1 技术栈（轻量级）

```
React (CRA) + Tailwind CSS + Framer Motion
```

### 2.2 核心组件设计

#### A. 主界面布局
```tsx
// frontend/src/App.tsx

<div className="min-h-screen bg-gradient-to-b from-indigo-900 to-purple-900">
  {/* 顶部：角色选择器 */}
  <RoleSelector currentRole={role} onRoleChange={setRole} />

  {/* 中部：对话区域 */}
  <div className="flex-1 flex flex-col">
    {/* 消息列表 */}
    <MessageList messages={messages} />

    {/* 音频可视化 */}
    <AudioVisualizer
      audioStream={audioStream}
      emotion={currentEmotion}
    />
  </div>

  {/* 底部：输入区域 */}
  <InputArea
    onSend={handleSend}
    onVoiceInput={handleVoiceInput}
    isRecording={isRecording}
  />
</div>
```

#### B. 音频可视化组件
```tsx
// frontend/src/components/AudioVisualizer.tsx

import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

export function AudioVisualizer({ audioStream, emotion }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!audioStream) return

    const audioContext = new AudioContext()
    const analyser = audioContext.createAnalyser()
    const source = audioContext.createMediaStreamSource(audioStream)
    source.connect(analyser)

    // 绘制波形
    const draw = () => {
      const data = analyser.getByteTimeDomainData()
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')

      // 根据情绪选择颜色
      const color = EMOTION_COLORS[emotion] || '#6366f1'

      // 绘制波形曲线
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.beginPath()

      for (let i = 0; i < data.length; i++) {
        const x = (i / data.length) * canvas.width
        const y = (data[i] / 128.0) * canvas.height / 2

        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }

      ctx.stroke()
      requestAnimationFrame(draw)
    }

    draw()
  }, [audioStream, emotion])

  return (
    <motion.div
      className="relative h-32 w-full"
      animate={{
        scale: emotion === 'excited' ? 1.1 : 1
      }}
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full rounded-lg bg-black/20"
      />

      {/* 情绪指示器 */}
      <motion.div
        className="absolute top-2 right-2 px-3 py-1 rounded-full"
        style={{ backgroundColor: EMOTION_COLORS[emotion] }}
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {emotion}
      </motion.div>
    </motion.div>
  )
}

const EMOTION_COLORS = {
  joy: '#fbbf24',      // 黄色
  sadness: '#3b82f6',  // 蓝色
  anger: '#ef4444',    // 红色
  neutral: '#6366f1',  // 紫色
  excited: '#f59e0b',  // 橙色
  calm: '#10b981'      // 绿色
}
```

#### C. 亲切的交互设计
```tsx
// frontend/src/components/InputArea.tsx

export function InputArea({ onSend, onVoiceInput, isRecording }) {
  return (
    <div className="p-4 bg-white/10 backdrop-blur-lg rounded-t-3xl">
      {/* 快捷回复建议 */}
      <div className="flex gap-2 mb-3 overflow-x-auto">
        <QuickReply text="讲个故事" onClick={() => onSend("讲个故事")} />
        <QuickReply text="我有点难过" onClick={() => onSend("我有点难过")} />
        <QuickReply text="聊聊天吧" onClick={() => onSend("聊聊天吧")} />
      </div>

      {/* 输入框 */}
      <div className="flex items-center gap-3">
        {/* 语音按钮 */}
        <motion.button
          whileTap={{ scale: 0.9 }}
          className="p-3 rounded-full bg-gradient-to-r from-pink-500 to-purple-500"
          onMouseDown={onVoiceInput}
        >
          <Mic className={isRecording ? "animate-pulse" : ""} />
        </motion.button>

        {/* 文本输入 */}
        <input
          className="flex-1 px-4 py-3 rounded-full bg-white/20 text-white placeholder-white/60"
          placeholder="说点什么吧，我在听..."
        />

        {/* 发送按钮 */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          className="p-3 rounded-full bg-indigo-500"
        >
          <Send />
        </motion.button>
      </div>
    </div>
  )
}
```

### 2.3 交互细节

- **打字效果**：流式文本逐字显示
- **情绪动画**：根据情绪改变背景渐变
- **音频反馈**：播放时波形跳动
- **角色切换**：平滑过渡动画

---

## 三、用户情绪感知与行为推理

### 3.1 情绪检测系统

#### A. 多模态情绪识别
```python
# src/emotion/emotion_detector.py

class EmotionDetector:
    """多模态情绪检测"""

    def __init__(self):
        # 文本情绪模型（轻量级）
        self.text_model = pipeline(
            "text-classification",
            model="lxyuan/distilbert-base-multilingual-cased-sentiment"
        )

    async def detect_emotion(
        self,
        text: str,
        audio_features: Optional[AudioFeatures] = None
    ) -> EmotionResult:
        """综合情绪检测"""

        # 1. 文本情绪
        text_emotion = self.text_model(text)[0]

        # 2. 音频情绪（如果有）
        audio_emotion = None
        if audio_features:
            audio_emotion = self._analyze_audio_emotion(audio_features)

        # 3. 融合结果
        final_emotion = self._fuse_emotions(text_emotion, audio_emotion)

        return EmotionResult(
            emotion=final_emotion,
            confidence=text_emotion['score'],
            signals={
                "text": text_emotion,
                "audio": audio_emotion
            }
        )
```

#### B. 用户行为推理
```python
# src/reasoning/behavior_reasoner.py

class BehaviorReasoner:
    """用户行为推理引擎"""

    def reason_user_state(self, context: UserContext) -> UserState:
        """推理用户当前状态"""

        # 1. 分析交互模式
        interaction_pattern = self._analyze_interactions(context.history)

        # 2. 情绪趋势分析
        emotion_trend = self._analyze_emotion_trend(context.emotion_history)

        # 3. 意图推断
        intent = self._infer_intent(context.current_input, interaction_pattern)

        # 4. 生成用户状态
        return UserState(
            current_emotion=context.current_emotion,
            emotion_trend=emotion_trend,  # "improving", "declining", "stable"
            interaction_style=interaction_pattern,  # "exploratory", "focused", "casual"
            inferred_intent=intent,  # "seeking_comfort", "learning", "entertainment"
            recommended_response=self._recommend_response(intent, emotion_trend)
        )

    def _recommend_response(self, intent: str, emotion_trend: str) -> str:
        """推荐响应策略"""

        if intent == "seeking_comfort" and emotion_trend == "declining":
            return "empathetic_support"  # 共情支持

        if intent == "learning" and emotion_trend == "stable":
            return "guided_explanation"  # 引导解释

        if intent == "entertainment":
            return "engaging_story"  # 有趣的故事

        return "friendly_conversation"  # 友好对话
```

### 3.2 集成到系统

```python
# 修改 src/server.py

async def handle_text_input(session_id: str, message: TextInputMessage):
    # 1. 检测用户情绪
    emotion = await emotion_detector.detect_emotion(message.content)

    # 2. 推理用户状态
    user_context = await get_user_context(session_id)
    user_state = behavior_reasoner.reason_user_state(user_context)

    # 3. 选择响应策略
    response_strategy = user_state.recommended_response

    # 4. 根据策略选择角色
    role = strategy_to_role(response_strategy)

    # 5. 生成响应
    response = await llm_router.chat(
        message.content,
        role=role,
        emotion_context=emotion
    )

    # 6. 发送情绪信息到前端
    await manager.send_json(session_id, {
        "type": "emotion_update",
        "emotion": emotion.emotion,
        "confidence": emotion.confidence
    })

    # 7. 发送响应
    await manager.send_text_chunk(session_id, response)
```

---

## 四、技术实现清单

### 4.1 后端实现

```bash
# 新增文件
src/personalization/
  ├── user_profile.py          # 用户画像
  ├── role_selector.py         # 角色选择器
  └── profile_manager.py       # 画像管理

src/skills/
  ├── role_skills.py           # 角色定义
  └── skill_loader.py          # Skill 加载器

src/emotion/
  ├── emotion_detector.py      # 情绪检测
  └── audio_emotion.py         # 音频情绪

src/reasoning/
  ├── behavior_reasoner.py     # 行为推理
  └── intent_inference.py      # 意图推断
```

### 4.2 前端实现

```bash
frontend/
  ├── src/
  │   ├── components/
  │   │   ├── AudioVisualizer.tsx    # 音频可视化
  │   │   ├── RoleSelector.tsx       # 角色选择
  │   │   ├── InputArea.tsx          # 输入区域
  │   │   └── EmotionIndicator.tsx   # 情绪指示
  │   ├── hooks/
  │   │   ├── useWebSocket.ts        # WebSocket 连接
  │   │   ├── useAudio.ts            # 音频处理
  │   │   └── useEmotion.ts          # 情绪状态
  │   └── App.tsx
  └── package.json
```

### 4.3 依赖安装

```bash
# 后端
pip install transformers torch

# 前端
npm install framer-motion tailwindcss
```

---

## 五、预期效果

### 5.1 个性化体验
- ✅ 3-5个独立角色，各有特色
- ✅ 自动根据用户选择合适角色
- ✅ 声音和语言风格统一

### 5.2 交互体验
- ✅ 现代化 UI，亲切友好
- ✅ 实时音频波形可视化
- ✅ 情绪动画反馈

### 5.3 智能感知
- ✅ 实时情绪检测
- ✅ 用户行为推理
- ✅ 智能响应策略

---

## 六、开发周期

| 模块 | 时间 | 优先级 |
|------|------|--------|
| 角色 Skill 系统 | 2天 | 🔥 高 |
| 前端基础框架 | 2天 | 🔥 高 |
| 情绪检测 | 1天 | 🔥 高 |
| 音频可视化 | 1天 | 📊 中 |
| 行为推理 | 2天 | 📊 中 |
| 集成测试 | 1天 | 📊 中 |

**总计：约 9 天**

---

## 七、快速启动命令

```bash
# 1. 克隆必需项目
cd O:\AII\app\voices\external
git clone https://github.com/huggingface/transformers.git --depth 1

# 2. 安装依赖
pip install transformers torch

# 3. 创建前端
npx create-react-app frontend --template typescript
cd frontend
npm install framer-motion tailwindcss @tailwindcss/ui

# 4. 启动开发
# 后端
python -m uvicorn src.server:app --reload

# 前端
cd frontend && npm start
```

---

**方案一完成！这是一个快速可落地的方案，核心功能完整，开发周期短。**

需要我继续设计**方案二**和**方案三**吗？