# 实时语音叙事系统

**企业级AI语音助手系统 - 支持情绪感知、多角色对话、语音交互**

## Docker 部署

### 启动（推荐）
```powershell
docker-compose up
```

服务将在 http://localhost:8000 启动。

### 说明
- **Edge TTS only** -- Docker 容器默认使用 Edge TTS 进行语音合成，无需 GPU
- **CosyVoice** -- 如需 CosyVoice（需要 GPU），请在本地直接运行，而非通过 Docker
- **Redis** -- Redis 服务默认不启动。如需启用，运行：`docker-compose --profile redis up`
- **前端** -- 前端 standalone 输出未配置，请单独启动前端：`cd frontend && npm run dev`

### 环境变量
容器会自动加载项目根目录的 `.env` 文件中的配置。通过 `SERVER_HOST` 和 `SERVER_PORT` 环境变量控制监听地址和端口。

## 🚀 快速启动

### 1. 启动后端
```powershell
双击运行：START.bat
```

### 2. 启动前端
```powershell
cd frontend
npm install    # 首次使用
npm run dev
```

### 3. 访问系统
打开浏览器：http://localhost:3000

## 📖 详细文档

- [快速开始指南](docs/user-guides/README_START.md)
- [用户使用手册](docs/user-guides/用户使用手册.md)
- [API配置指南](docs/user-guides/USER_GUIDE.md)

## 🎯 核心功能

- 🎭 **多角色AI** - 支持动态创建/管理角色，SillyTavern 兼容格式
- 😊 **情绪感知** - LLM驱动的多维情绪权重分析 + 关键词fallback
- 🗣️ **语音交互** - WebSocket 实时流式对话，语音打断检测
- 🧠 **中文NLP** - 分词、情感分析、实体识别
- 💾 **三层记忆系统** - 短期(30轮)→长期(语义向量检索)→核心记忆(永不遗忘)
- 💿 **数据库持久化** - SQLAlchemy ORM，支持 SQLite / PostgreSQL 切换
- 🎨 **3D可视化** - Three.js 情绪球体 + 粒子系统
- 🔌 **多Provider路由** - DeepSeek + Claude 双LLM路由，自动故障切换

## ⚙️ 配置API密钥

编辑 `.env` 文件：
```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key_here
```

获取密钥：https://platform.deepseek.com/

## 📊 项目状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 后端AI核心 | ✅ 100% | 情绪检测、用户画像、多角色系统 |
| 前端UI | ✅ 100% | 3D可视化、聊天界面、角色管理页 |
| 数据库持久化 | ✅ 100% | SQLAlchemy ORM，SQLite/PostgreSQL |
| 音频处理 | ✅ 100% | 录音、播放、VAD检测、TTS合成 |
| 中文NLP | ✅ 100% | 分词、情感分析、NER、文本分类 |
| 单元测试 | ✅ 98/98 passing | 存储层、情绪、缓存、音频工具等 |

## 📁 项目结构

```
O:\AII\app\voices\
├── START.bat              # 启动脚本
├── run_server_auto_port.py # 服务器主程序
├── check_environment.py   # 环境检查
├── src/                   # 源代码
│   ├── emotion/          # 情绪检测
│   ├── nlp/              # 中文NLP
│   ├── audio/            # 音频处理
│   ├── tts/              # 语音合成
│   └── server.py         # WebSocket服务器
├── frontend/             # 前端应用
├── tests/                # 测试代码
└── docs/                 # 文档
    ├── user-guides/      # 用户指南
    ├── design/           # 设计文档
    └── technical/        # 技术文档
```

## 🔧 环境要求

- Python 3.11.4
- Node.js 18+
- 现代浏览器（Chrome/Edge推荐）

## 📞 获取帮助

- 检查环境：运行 `check.bat`
- 查看日志：控制台输出
- 详细文档：`docs/` 目录

---

**开始体验：双击 START.bat → 打开浏览器 → 开始对话** 🎉