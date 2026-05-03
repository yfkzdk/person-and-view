# 实时语音叙事系统 - 快速启动指南

## 🚀 快速启动（3步）

### 方法1：使用启动脚本（推荐）

```powershell
# 1. 进入项目目录
cd O:\AII\app\voices

# 2. 双击运行
start_server_fixed.bat
```

### 方法2：手动启动

```powershell
# 1. 进入项目目录
cd O:\AII\app\voices

# 2. 检查环境
"C:\Users\yfk\AppData\Local\Programs\Python\Python311\python.exe" check_environment.py

# 3. 启动服务器
"C:\Users\yfk\AppData\Local\Programs\Python\Python311\python.exe" run_server.py
```

## ⚙️ 配置API密钥（可选）

创建 `.env` 文件：

```env
# DeepSeek API（推荐，性价比高）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat

# 或使用 Anthropic Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_api_key_here
# LLM_MODEL=claude-3-5-sonnet-20241022
```

**获取API密钥：**
- DeepSeek: https://platform.deepseek.com/
- Anthropic: https://console.anthropic.com/

## 🌐 启动前端

```powershell
# 1. 进入前端目录
cd O:\AII\app\voices\frontend

# 2. 安装依赖（首次使用）
npm install

# 3. 启动开发服务器
npm run dev
```

访问: http://localhost:3000

## 📖 使用说明

### 基本对话
1. 打开浏览器访问 http://localhost:3000
2. 在底部输入框输入文字
3. 点击"发送"按钮
4. AI会根据您的情绪做出回应

### 语音交互
1. 点击麦克风按钮开始录音
2. 说话时系统会自动检测
3. 松开后AI会语音回复

### 情绪感知
- 顶部3D球体会显示AI当前情绪
- 球体颜色和动画会根据情绪变化
- AI会根据您的情绪调整回应方式

## 🔧 常见问题

### Q1: 启动报错 "ModuleNotFoundError"
**解决：** 使用Python 3.11.4，不要用虚拟环境
```powershell
# 使用完整路径
"C:\Users\yfk\AppData\Local\Programs\Python\Python311\python.exe" run_server.py
```

### Q2: 前端无法连接后端
**检查：**
1. 后端是否在 http://localhost:8000 运行
2. 浏览器控制台是否有错误
3. 防火墙是否阻止连接

### Q3: AI没有回复
**检查：**
1. `.env` 文件中的API密钥是否正确
2. API余额是否充足
3. 后端日志是否有错误信息

### Q4: 语音功能不工作
**解决：**
1. 使用Chrome或Edge浏览器
2. 允许浏览器访问麦克风
3. 生产环境需要HTTPS

## 📊 系统架构

```
前端 (Next.js + React)
    ↓ WebSocket
后端 (FastAPI)
    ├── 情绪检测 (BERT)
    ├── 中文NLP (jieba)
    ├── 语音合成 (Edge TTS)
    ├── VAD检测 (Silero)
    └── LLM (DeepSeek/Claude)
```

## 🎯 核心功能

1. **多角色AI** - 5种角色自动切换
2. **情绪感知** - 识别用户情绪
3. **语音交互** - 语音输入输出
4. **个性化** - 学习用户偏好
5. **中文NLP** - 智能中文处理

## 📞 技术支持

- 文档: `docs/` 目录
- 日志: 控制台输出
- 问题: 查看GitHub Issues

---

**祝您使用愉快！** 🎉