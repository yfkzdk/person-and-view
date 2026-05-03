# CosyVoice 语音对话集成计划

## 目标
将 CosyVoice3 零样本语音克隆集成到 WebSocket 对话系统，实现端到端语音对话。

## 前置条件（已验证）
- [x] CosyVoice3 推理成功（7秒音频，338KB WAV）
- [x] 参考音频已准备：ref_audio/tong_jincheng_ref.wav
- [x] 所有 Python 依赖已安装（torch, torchaudio, einops, scipy, tiktoken, regex, tqdm, pyarrow, PyYAML, whisper, phonemizer, Unidecode）

---

## 任务清单

### 任务1：补全 CosyVoice 依赖（一次性）
**文件**: `external/CosyVoice/requirements_win.txt`
**操作**: 更新 requirements_win.txt，加入所有缺失的运行时依赖
**验证**: `pip install -r requirements_win.txt` 无报错 + 完整 import 测试通过

需要添加的包（不在原 requirements_win.txt 中）：
- torch (cu121)
- torchaudio (cu121)
- einops
- scipy
- openai-whisper
- tiktoken
- regex
- tqdm
- pyarrow
- PyYAML
- phonemizer
- Unidecode
- gdown
- wget

### 任务2：修复后端代码 — 统一 TTS 接口
**问题**: server.py 和 dialogue_manager.py 引用已删除的 TTSStreamer 类
**文件**:
- `src/server.py` — 已部分修改，需完成
- `src/dialogue/dialogue_manager.py` — 已部分修改，需完成
- `src/tts/tts_streamer.py` — 已重写为统一接口

**具体修改**:

2a. `src/server.py`:
- 移除 `tts_streamers` 字典（已完成）
- 移除 TTSStreamer 初始化代码（已完成）
- 修改 `handle_text_input` 中的 TTS 调用：`tts_streamer.stream_synthesize(full_response)` → `get_tts_audio(full_response)`
- 修改 `cleanup_session`：移除 `tts_streamers` 引用

2b. `src/dialogue/dialogue_manager.py`:
- 已改为 `from src.tts.tts_streamer import get_tts_audio`
- 已移除 TTSStreamer 初始化
- 已改为 `async for audio_chunk in get_tts_audio(full_text)`
- 需验证：移除未使用的 TTSConfig/VoiceConfig import

2c. `src/tts/tts_streamer.py`:
- 当前实现正确，CosyVoice 输出 WAV 分 8KB 块发送
- 需添加：音频格式标记（让前端知道是 MP3 还是 WAV）

### 任务3：修复前端音频播放 — 支持 WAV 格式
**问题**: 前端硬编码 `audio/mp3` MIME type，CosyVoice 输出 WAV
**文件**:
- `frontend/src/app/page.tsx` — 第125行
- `src/models/messages.py` — AudioMessage
- `src/websocket/connection_manager.py` — send_audio

**具体修改**:

3a. `src/models/messages.py`:
- AudioMessage 添加 `format: str = "mp3"` 字段

3b. `src/tts/tts_streamer.py`:
- `get_tts_audio` yield 时附带格式信息（通过修改返回结构或添加全局状态）
- 方案：在 tts_streamer 中设置模块级变量 `current_format`，ConnectionManager 读取

3c. `src/websocket/connection_manager.py`:
- `send_audio` 方法接受 `format` 参数，传入 AudioMessage

3d. `frontend/src/app/page.tsx`:
- 第125行：`{ type: 'audio/mp3' }` → `{ type: \`audio/${data.format || 'mp3'}\` }`
- 从 WebSocket 消息中读取 format 字段

### 任务4：修复 run_server_auto_port.py
**问题**: cleanup_session 引用不存在的 llm_routers 和 tts_streamers 字典
**文件**: `run_server_auto_port.py`

**具体修改**:
- cleanup_session 中移除 `llm_routers` 和 `tts_streamers` 引用
- 改为清理 `dialogue_managers`
- 移除顶部 `from src.tts.tts_streamer import TTSStreamer` 和 `from src.models.tts_config import TTSConfig, VoiceConfig`

### 任务5：端到端测试
**操作**:
1. 启动后端服务器（START.bat 或 python run_server_auto_port.py）
2. 启动前端（npm run dev）
3. 在前端输入文字，验证：
   - WebSocket 连接成功
   - LLM 生成文本回复
   - TTS 合成音频（Edge TTS 模式先测）
   - 前端播放音频
4. 切换 TTS_PROVIDER=cosyvoice，重启后端
5. 验证 CosyVoice 模式：
   - 音频生成成功
   - 前端播放 WAV 音频
   - 音色为童金成声线

---

## 风险点
1. **CosyVoice 推理速度**: RTF=1.26（7秒音频需9秒生成），对话延迟较高
2. **GPU 内存**: CosyVoice 推理占用 GPU，与 VSCode 共享 8GB VRAM，可能需要关闭 VSCode
3. **WAV 文件大小**: WAV 比 MP3 大约10倍，网络传输量增加
4. **前端音频格式**: 需确保 Blob MIME type 正确，否则浏览器无法解码
