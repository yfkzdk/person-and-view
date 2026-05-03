# 🚀 三个优化方案

## ✅ 已修复的问题

### 1. 音频文件分离 ✅
- **问题**：多次对话的音频混在一个文件
- **解决**：每次对话生成独立文件 `output_audio_1.wav`, `output_audio_2.wav`...
- **实现**：
  - 添加音频计数器 `audio_counters`
  - 音频消息包含 `audio_index` 和 `is_new_file` 标记
  - 客户端根据序号保存到不同文件

### 2. 连接保活 ✅
- **问题**：连接一段时间后自动断开
- **解决**：添加心跳机制，每30秒发送心跳保持连接
- **实现**：
  - 服务器端心跳任务 `heartbeat()`
  - 客户端接收心跳消息 `{"type": "heartbeat"}`
  - 防止 WebSocket 超时断开

### 3. 文本清理 ✅
- **问题**：emoji 和情绪文字被朗读出来
- **解决**：TTS 前自动过滤 emoji、markdown 符号、情绪词
- **实现**：
  - 创建 `text_cleaner.py` 工具
  - 正则表达式移除 emoji (Unicode 范围)
  - 移除 markdown 格式符号
  - TTS streamer 自动调用清理函数

---

## 🎯 优化方案一：模拟声音系统

### 目标
实现多种声音角色，支持语气、情感、语速调节

### 技术方案

#### 1.1 多角色声音库
```python
# src/tts/voice_profiles.py
VOICE_PROFILES = {
    "narrator": {  # 默认旁白
        "voice": "XiaoxiaoNeural",
        "rate": 1.0,
        "pitch": 0,
        "style": "narration"
    },
    "excited": {  # 兴奋
        "voice": "XiaoyiNeural",
        "rate": 1.2,
        "pitch": 10,
        "style": "cheerful"
    },
    "calm": {  # 平静
        "voice": "YunxiNeural",
        "rate": 0.9,
        "pitch": -5,
        "style": "calm"
    },
    "dramatic": {  # 戏剧化
        "voice": "XiaoxiaoNeural",
        "rate": 0.8,
        "pitch": 5,
        "style": "emotional"
    }
}
```

#### 1.2 情感检测
```python
# src/nlp/emotion_detector.py
from transformers import pipeline

class EmotionDetector:
    def __init__(self):
        self.classifier = pipeline(
            "text-classification",
            model="bhadresh-savani/distilbert-base-uncased-emotion"
        )

    def detect_emotion(self, text: str) -> str:
        """检测文本情感"""
        result = self.classifier(text)[0]
        emotion = result['label']  # joy, sadness, anger, fear, surprise, love

        # 映射到声音配置
        emotion_voice_map = {
            "joy": "excited",
            "sadness": "calm",
            "anger": "dramatic",
            "surprise": "excited",
            "love": "calm",
            "fear": "dramatic"
        }

        return emotion_voice_map.get(emotion, "narrator")
```

#### 1.3 动态声音切换
```python
# 修改 TTS streamer
async def stream_synthesize(self, text: str):
    # 检测情感
    emotion = self.emotion_detector.detect_emotion(text)

    # 选择声音配置
    voice_profile = VOICE_PROFILES[emotion]

    # 应用配置
    config = TTSConfig(
        voice=VoiceConfig(**voice_profile)
    )

    # 合成音频
    async for chunk in self._synthesize(text, config):
        yield chunk
```

### 实现步骤
1. 创建声音配置文件 `voice_profiles.py`
2. 集成情感检测模型（可选：使用轻量级模型或规则匹配）
3. 修改 TTS streamer 支持动态配置
4. 添加导演指令支持：`[voice:excited]` 切换声音

### 预期效果
- 自动根据文本情感选择合适声音
- 支持手动指定声音角色
- 更生动、更有表现力的语音输出

---

## 🎯 优化方案二：接入语言行为 Skill

### 目标
集成 Claude 的语言行为 skill，实现更智能的对话理解和生成

### 技术方案

#### 2.1 集成 Claude Skill 系统
```python
# src/llm/claude_skill_integration.py
from anthropic import Anthropic

class ClaudeSkillIntegration:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.skills = self._load_skills()

    def _load_skills(self):
        """加载可用的 skills"""
        return {
            "narrative": self._load_narrative_skill(),
            "dialogue": self._load_dialogue_skill(),
            "description": self._load_description_skill()
        }

    async def generate_with_skill(
        self,
        prompt: str,
        skill_name: str = "narrative"
    ):
        """使用指定 skill 生成内容"""
        skill = self.skills[skill_name]

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"{skill}\n\n{prompt}"
            }]
        )

        return response.content[0].text
```

#### 2.2 语言行为 Skills 定义
```markdown
# narrative.skill
## 目标
生成引人入胜的叙事内容，适合语音朗读

## 规则
1. 使用生动的语言和描述
2. 避免过长的句子（适合语音）
3. 自然地分段和停顿
4. 包含情感和语气变化
5. 使用导演指令标记：[pause], [slow], [fast]

## 示例
用户：讲一个关于勇气的故事
输出：
在一个风雨交加的夜晚... [pause]
年轻的冒险者站在悬崖边... [slow]
她深吸一口气，眼神坚定... [fast]
然后纵身一跃！
```

#### 2.3 智能对话路由
```python
# src/llm/smart_router.py
class SmartRouter:
    def route(self, user_input: str) -> str:
        """根据输入选择合适的 skill"""
        # 关键词匹配
        if any(kw in user_input for kw in ["讲个故事", "说说", "叙述"]):
            return "narrative"

        if any(kw in user_input for kw in ["对话", "聊天", "讨论"]):
            return "dialogue"

        if any(kw in user_input for kw in ["描述", "介绍", "说明"]):
            return "description"

        # 默认
        return "narrative"
```

### 实现步骤
1. 创建 skill 定义文件（`.skill` 格式）
2. 实现 skill 加载和管理系统
3. 集成到 LLM router
4. 添加智能路由逻辑
5. 测试不同 skill 的效果

### 预期效果
- 更专业的叙事能力
- 自动选择合适的生成策略
- 更自然的语音节奏和停顿
- 支持多种对话风格

---

## 🎯 优化方案三：前端页面优化

### 目标
创建现代化的 Web UI，提供更好的用户体验

### 技术方案

#### 3.1 技术栈选择
- **前端框架**: React + TypeScript
- **UI 库**: shadcn/ui (Radix UI + Tailwind CSS)
- **状态管理**: Zustand
- **WebSocket**: native WebSocket API
- **音频可视化**: Web Audio API + Canvas

#### 3.2 核心功能模块

##### A. 对话界面
```tsx
// components/ChatInterface.tsx
export function ChatInterface() {
  return (
    <div className="flex flex-col h-screen">
      {/* 顶部状态栏 */}
      <StatusBar />

      {/* 消息列表 */}
      <MessageList messages={messages} />

      {/* 音频可视化 */}
      <AudioVisualizer />

      {/* 输入区域 */}
      <InputArea
        onSend={handleSend}
        onVoiceInput={handleVoiceInput}
      />
    </div>
  )
}
```

##### B. 音频可视化
```tsx
// components/AudioVisualizer.tsx
export function AudioVisualizer({ audioStream }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const audioContext = new AudioContext()
    const analyser = audioContext.createAnalyser()
    const source = audioContext.createMediaStreamSource(audioStream)

    source.connect(analyser)

    // 绘制波形
    const draw = () => {
      const data = analyser.getByteTimeDomainData()
      // Canvas 绘制逻辑
      requestAnimationFrame(draw)
    }

    draw()
  }, [audioStream])

  return <canvas ref={canvasRef} />
}
```

##### C. 语音输入
```tsx
// hooks/useVoiceInput.ts
export function useVoiceInput() {
  const [isRecording, setIsRecording] = useState(false)

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true
    })

    const mediaRecorder = new MediaRecorder(stream)
    const chunks = []

    mediaRecorder.ondataavailable = (e) => {
      chunks.push(e.data)
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' })
      sendAudioToServer(blob)
    }

    mediaRecorder.start()
    setIsRecording(true)
  }

  return { isRecording, startRecording, stopRecording }
}
```

#### 3.3 UI 设计要点

##### 视觉设计
- 深色主题（护眼）
- 渐变背景（现代感）
- 圆角卡片（友好）
- 流畅动画（专业）

##### 交互设计
- 实时打字效果（流式文本）
- 音频波形动画（可视化）
- 语音按钮（长按录音）
- 快捷键支持（Ctrl+Enter 发送）

##### 响应式设计
- 桌面端：双栏布局（对话 + 设置）
- 移动端：单栏布局（底部输入）
- 平板：自适应布局

#### 3.4 项目结构
```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageList.tsx
│   │   ├── AudioVisualizer.tsx
│   │   ├── InputArea.tsx
│   │   └── StatusBar.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useVoiceInput.ts
│   │   └── useAudio.ts
│   ├── stores/
│   │   └── chatStore.ts
│   ├── lib/
│   │   ├── websocket.ts
│   │   └── audio.ts
│   └── App.tsx
├── public/
├── package.json
└── tailwind.config.js
```

### 实现步骤
1. 初始化 React 项目：`create-next-app`
2. 安装依赖：shadcn/ui, zustand, tailwind
3. 实现核心组件
4. 集成 WebSocket 连接
5. 实现音频录制和播放
6. 添加音频可视化
7. 优化 UI 和动画
8. 测试和部署

### 预期效果
- 现代化、美观的界面
- 实时音频可视化
- 语音输入支持
- 流畅的用户体验
- 响应式设计（支持移动端）

---

## 📊 优化方案对比

| 方案 | 难度 | 时间 | 效果 | 优先级 |
|------|------|------|------|--------|
| 模拟声音 | ⭐⭐ | 2-3天 | 高 | 🔥 高 |
| 语言行为 Skill | ⭐⭐⭐ | 3-5天 | 很高 | 🔥 高 |
| 前端优化 | ⭐⭐⭐⭐ | 5-7天 | 很高 | 📊 中 |

## 🎯 推荐实施顺序

### 阶段1：声音系统（1周）
1. 实现多角色声音
2. 添加情感检测
3. 测试效果

### 阶段2：语言行为（1周）
1. 定义 skills
2. 集成到系统
3. 优化生成质量

### 阶段3：前端优化（2周）
1. 搭建前端框架
2. 实现核心功能
3. 优化 UI/UX
4. 部署上线

## 🚀 快速开始

现在可以：
1. **测试修复效果**：运行客户端体验改进
2. **选择优化方案**：根据需求选择实施方案
3. **开始开发**：我可以帮你实现任一方案

需要我帮你实现哪个优化方案？