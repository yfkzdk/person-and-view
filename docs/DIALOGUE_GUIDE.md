# 对话功能使用指南

## ✅ 功能已实现

对话功能已完全实现，包括：
- ✅ 角色模拟对话
- ✅ 情绪感知
- ✅ 记忆系统
- ✅ 语音合成（可选）
- ✅ 命令行界面
- ✅ WebSocket实时对话

## 🚀 快速开始

### 方式1：命令行对话（推荐）

**启动方式**：
```bash
# 方式1：双击批处理文件
双击 CHAT_CLI.bat

# 方式2：命令行启动
python chat_cli.py
```

**使用示例**：
```
🎭 AI人物对话系统
================================================================================

命令:
  /switch <角色名>  - 切换角色
  /list             - 列出所有角色
  /info             - 显示当前角色信息
  /clear            - 清空对话历史
  /save             - 保存对话
  /quit             - 退出程序
  /help             - 显示帮助
================================================================================

可用角色:
  1. 小云 - 一位温暖、专业的心理咨询师...
  2. 小明 - 一个乐观、幽默、讲义气的好朋友...
  3. 分析师 - 一位善于理性分析、逻辑思考的顾问...

请选择角色 (输入名称或序号，默认: 小云):
> 1

当前角色: 小云
描述: 一位温暖、专业的心理咨询师...
性格: 温暖、同理心强、专业、耐心
--------------------------------------------------------------------------------

开始对话 (输入消息或命令):

你: 你好
小云: [中性 30%] 你好！很高兴见到你。有什么我可以帮你的吗？

你: 我最近感觉很焦虑
小云: [焦虑 70%] 感受到你的焦虑，这本身就说明你对自己有着敏锐的觉察...

你: /switch 小明
✅ 已切换到角色: 小明

你: 我今天心情不好
小明: [悲伤 50%] 哎呀，谁惹你不开心了？告诉我，我帮你出气！

你: /quit
正在保存对话...
再见！👋
```

### 方式2：WebSocket实时对话（前端）

**启动后端**：
```bash
# 方式1：双击批处理文件
双击 START.bat

# 方式2：命令行启动
python run_server_auto_port.py
```

**前端连接**：
- 前端会自动连接到后端WebSocket
- 发送消息格式：
```json
{
  "type": "text_input",
  "content": "你好",
  "session_id": "client1"
}
```

- 切换角色：
```json
{
  "type": "switch_character",
  "character_name": "小明"
}
```

- 接收消息类型：
  - `text_chunk` - 文本块
  - `audio` - 音频数据
  - `emotion` - 情绪信息
  - `status` - 状态更新

### 方式3：Python代码调用

```python
import asyncio
from src.dialogue.dialogue_manager import DialogueManager

async def chat():
    # 创建对话管理器
    dialogue = DialogueManager(
        character_name="小云",
        enable_memory=True,
        enable_emotion=True,
        enable_tts=True  # 启用语音
    )

    # 对话
    user_input = "你好"

    async for message in dialogue.chat(user_input, return_audio=True):
        if message["type"] == "emotion":
            print(f"情绪: {message['emotion']}")

        elif message["type"] == "text_chunk" and not message["is_final"]:
            print(message["content"], end="", flush=True)

        elif message["type"] == "audio" and not message["is_final"]:
            # 播放音频
            audio_data = message["data"]
            # ... 音频播放代码

    # 保存状态
    dialogue.save_state()

asyncio.run(chat())
```

## 🎭 可用角色

### 1. 小云 - 心理咨询师
- **性格**: 温暖、同理心强、专业、耐心
- **特点**: 善于倾听和共情
- **适用**: 心理咨询、情感支持
- **口头禅**: "我理解你的感受"、"让我们一起来看看"

### 2. 小明 - 幽默朋友
- **性格**: 幽默、乐观、讲义气、随和
- **特点**: 喜欢开玩笑，关键时刻靠谱
- **适用**: 日常聊天、娱乐
- **口头禅**: "哈哈"、"没问题！"、"包在我身上"

### 3. 分析师 - 理性顾问
- **性格**: 理性、严谨、善于分析、客观
- **特点**: 逻辑清晰，客观专业
- **适用**: 问题分析、决策支持
- **口头禅**: "让我来分析一下"、"从...角度来看"

## 🔧 高级功能

### 1. 角色切换
```python
# Python代码
dialogue.switch_character("小明")

# 命令行
/switch 小明

# WebSocket
发送 {"type": "switch_character", "character_name": "小明"}
```

### 2. 记忆管理
```python
# 清空对话历史
dialogue.clear_conversation()

# 保存状态
dialogue.save_state()

# 获取记忆上下文
context = dialogue.memory.get_relevant_context("篮球")
```

### 3. 情绪分析
```python
# 分析情绪
emotion = dialogue.emotion_responder.analyze_user_emotion("我很焦虑")
print(f"情绪: {emotion.primary_emotion}")
print(f"强度: {emotion.intensity}")
```

### 4. 自定义角色
```python
from src.utils.person_distiller import PersonDistiller

# 从对话样本蒸馏
dialogues = [
    ("用户输入1", "角色回复1"),
    ("用户输入2", "角色回复2"),
]

distiller = PersonDistiller()
profile = distiller.distill_from_dialogues(
    name="自定义角色",
    role="角色定位",
    dialogues=dialogues
)
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
[TTS合成] → 生成语音（可选）
    ↓
[记忆存储] → 保存对话
    ↓
输出回复
```

## 📁 文件说明

```
O:\AII\app\voices\
├── chat_cli.py                    # 命令行对话工具
├── CHAT_CLI.bat                   # 启动脚本
├── test_simple_dialogue.py        # 简单测试
├── src\
│   └── dialogue\
│       └── dialogue_manager.py    # 对话管理器
├── characters\                    # 角色卡片存储
│   ├── 小云.json
│   ├── 小明.json
│   └── 分析师.json
└── memory\                        # 记忆数据存储
    └── 小云\
        └── long_term.json
```

## 🎯 测试结果

✅ **对话功能测试通过**
- 情绪检测：正常
- 角色模拟：正常
- 记忆系统：正常
- LLM生成：正常
- 语音合成：正常

## 💡 使用建议

1. **选择合适的角色**
   - 心理咨询 → 小云
   - 日常聊天 → 小明
   - 问题分析 → 分析师

2. **利用记忆系统**
   - 系统会自动记住重要信息
   - 可以跨会话保持上下文

3. **观察情绪反馈**
   - 系统会显示检测到的情绪
   - 根据情绪调整回复策略

4. **保存对话**
   - 使用 `/save` 或自动保存
   - 下次对话会恢复记忆

---

**对话功能已完全实现，可以直接使用！**

启动方式：
- **命令行**: 双击 `CHAT_CLI.bat`
- **WebSocket**: 双击 `START.bat` 启动后端
