"""
简单测试 - 验证客户端连接
"""
import asyncio
import sys
import websockets
import json

# 设置 UTF-8 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def test_connection():
    """测试 WebSocket 连接"""
    print("="*60)
    print("🧪 测试 WebSocket 连接")
    print("="*60)
    print()

    try:
        print("🔗 连接到 ws://localhost:8000/ws/test-session...")
        websocket = await websockets.connect("ws://localhost:8000/ws/test-session")
        print("✅ 连接成功！")
        print()

        # 接收初始状态
        print("📥 接收初始状态...")
        message = await websocket.recv()
        data = json.loads(message)
        print(f"📊 收到消息: {data}")
        print()

        # 发送文本消息
        print("📤 发送文本消息: 你好")
        await websocket.send(json.dumps({
            "type": "text_input",
            "content": "你好",
            "session_id": "test-session"
        }))
        print("✅ 发送成功")
        print()

        # 接收响应
        print("📥 等待响应...")
        for i in range(5):
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"📊 响应 {i+1}: {data}")

                if data.get("type") == "status" and data.get("status") == "listening":
                    print("✅ 处理完成")
                    break
            except asyncio.TimeoutError:
                print("⏱️ 5秒内无消息")
                break

        # 关闭连接
        await websocket.close()
        print()
        print("🔌 连接已关闭")
        print()
        print("="*60)
        print("✅ 测试成功！")
        print("="*60)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_connection())