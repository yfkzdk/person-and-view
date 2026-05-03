# 🎯 最终使用指南 - 3步启动

## ✅ 第1步：启动后端（双击这个文件）

```
O:\AII\app\voices\START.bat
```

**看到这个表示成功：**
```
Server: http://localhost:8002  ← 注意这个端口数字
INFO: Uvicorn running on http://0.0.0.0:8002
```

**重要：** 记住显示的端口数字（可能是8002、8003等）

---

## ✅ 第2步：启动前端

打开PowerShell，运行：

```powershell
cd O:\AII\app\voices\frontend
npm install          # 首次使用需要
npm run dev
```

**访问：** http://localhost:3000

---

## ✅ 第3步：配置AI（可选）

编辑 `O:\AII\app\voices\.env`：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的密钥
```

**获取密钥：** https://platform.deepseek.com/

---

## 🎮 现在可以使用了！

1. 打开浏览器：http://localhost:3000
2. 输入文字，点击发送
3. AI会根据您的情绪回应
4. 观察顶部3D球体的情绪变化

---

## 🔧 如果前端连接失败

前端默认连接8000端口，如果后端用了其他端口（如8002），需要修改前端配置：

编辑 `O:\AII\app\voices\frontend\src\hooks\useWebSocket.ts`：

```typescript
const WS_URL = 'ws://localhost:8002/ws/${sessionId}'  // 改成实际端口
```

---

## 📝 快速测试命令

```powershell
# 检查环境
cd O:\AII\app\voices
.\check.bat

# 启动服务器
.\START.bat
```

---

**就这么简单！双击 START.bat → 打开浏览器 → 开始对话** 🚀