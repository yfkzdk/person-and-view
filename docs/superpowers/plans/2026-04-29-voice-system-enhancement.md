# 语音对话系统增强计划

## 目标
实现6个功能：麦克风录音、角色切换、参考音频优化、对话记忆持久化、流式TTS、Docker部署

---

## 任务1：前端接入麦克风
**文件**: `frontend/src/app/page.tsx`, 新建 `frontend/src/components/VoiceRecorder.tsx`
**具体**:
- 创建 VoiceRecorder 组件，使用 MediaRecorder API 录音
- 录音格式：webm/opus，采样率 16kHz
- 按住说话 / 点击切换模式
- 录音完成后通过 WebSocket 发送二进制音频数据
- 添加录音状态指示器（录音中/空闲）
- 在 page.tsx 中集成 VoiceRecorder，替换纯文字输入
- 保留文字输入作为备选

## 任务2：角色切换
**文件**: `frontend/src/app/page.tsx`, `src/server.py`, `src/dialogue/dialogue_manager.py`, 新建 `frontend/src/components/CharacterSelector.tsx`
**具体**:
- 后端：添加 WebSocket 消息类型 `switch_character`，调用 DialogueManager.switch_character()
- 后端：添加 `list_characters` 消息类型，返回可用角色列表
- 前端：创建 CharacterSelector 下拉组件
- 前端：发送 switch_character 消息，接收确认
- 角色切换后清空对话历史显示

## 任务3：参考音频替换
**文件**: `src/tts/cosyvoice_client.py`, `src/config.py`, `src/tts/tts_streamer.py`
**具体**:
- config.py 添加 COSYVOICE_REF_TEXT_MAP 配置（不同参考音频对应不同文本）
- cosyvoice_client.py 支持动态切换 ref_audio 和 ref_text
- tts_streamer.py 的 _cosyvoice_synthesize 支持传入 voice 参数指定参考音频
- 在 ref_audio/ 目录下放一个 README 说明如何添加新参考音频
- 不删除现有 tong_jincheng_ref.wav

## 任务4：对话记忆持久化
**文件**: `src/memory/smart_memory.py`, `src/state/session_manager.py`, `src/config.py`
**具体**:
- SmartMemorySystem 添加 save_to_file() 和 load_from_file() 方法
- 使用 JSON 文件存储对话历史（memory/{character_name}/history.json）
- DialogueManager 初始化时自动加载历史
- 每次对话后自动保存
- 添加 MAX_HISTORY_FILE_SIZE 配置防止文件过大
- 不引入 Redis（当前 REDIS_ENABLED=false），用文件持久化即可

## 任务5：流式TTS优化
**文件**: `src/tts/cosyvoice_client.py`, `src/tts/tts_streamer.py`
**具体**:
- cosyvoice_client.py 添加 synthesize_streaming() 方法
- 使用 CosyVoice 的 stream=True 模式
- 每个音频块生成后立即写入临时文件并返回
- tts_streamer.py 的 _cosyvoice_synthesize 改为调用流式方法
- 流式模式下每个 chunk 是独立的 WAV 片段
- 注意：流式 WAV 需要在前端拼接或使用 PCM 原始数据

## 任务6：Docker部署
**文件**: 新建 `Dockerfile`, `docker-compose.yml`, `.dockerignore`
**具体**:
- Dockerfile：基于 python:3.11-slim
- 多阶段构建：前端 npm build → 后端 Python
- docker-compose.yml：app 服务 + 可选 Redis 服务
- 环境变量通过 .env 文件注入
- 暴露端口 8000
- .dockerignore 排除 venv, node_modules, __pycache__, .git
- 注意：CosyVoice 需要 GPU，Docker 里用 Edge TTS 模式
- 添加 README 说明 Docker 启动命令
