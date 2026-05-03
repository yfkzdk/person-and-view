"""
完整演示 - 展示优化后的输出效果
"""
import asyncio
import sys
import websockets
import json
import base64

# 设置 UTF-8 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def demo():
    """完整演示"""
    print("="*60)
    print("🎙️ 实时语音叙事系统 - 完整演示")
    print("="*60)
    print()

    try:
        print("🔗 连接到 ws://localhost:8000/ws/demo...")
        websocket = await websockets.connect("ws://localhost:8000/ws/demo")
        print("✅ 连接成功！")
        print()

        # 接收初始状态
        message = await websocket.recv()
        data = json.loads(message)
        print(f"📊 初始状态: {data['status']}")
        print()

        # 发送文本消息
        print("="*60)
        print("💬 发送消息: 你好，请简单介绍一下你自己")
        print("="*60)
        print()

        await websocket.send(json.dumps({
            "type": "text_input",
            "content": "你好，请简单介绍一下你自己",
            "session_id": "demo"
        }))

        # 接收响应
        audio_count = 0
        audio_bytes_total = 0
        text_parts = []

        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "status":
                    status = data.get("status")
                    if status == "processing":
                        print("📊 状态: 正在处理...")
                        print()
                        print("📝 DeepSeek 生成: ", end="", flush=True)

                    elif status == "listening":
                        print()  # 换行
                        print()
                        if audio_count > 0:
                            print(f"🔊 音频合成完成: {audio_count} 个块, 共 {audio_bytes_total} bytes")
                            print("💾 音频已保存到 output_audio.wav")
                            print()
                        print("✅ 处理完成，系统回到监听状态")
                        break

                elif msg_type == "text_chunk":
                    content = data.get("content", "")
                    is_final = data.get("is_final", False)

                    if content:
                        print(content, end="", flush=True)
                        text_parts.append(content)

                    if is_final:
                        print()  # 换行
                        print("✅ 文本生成完成")

                elif msg_type == "audio":
                    audio_data = data.get("data", "")
                    if audio_data:
                        audio_bytes = base64.b64decode(audio_data)
                        audio_count += 1
                        audio_bytes_total += len(audio_bytes)

                        # 保存音频
                        with open("output_audio.wav", "ab") as f:
                            f.write(audio_bytes)

                elif msg_type == "error":
                    error_msg = data.get("message", "unknown error")
                    print(f"❌ 错误: {error_msg}")
                    break

            except asyncio.TimeoutError:
                print("⏱️ 超时，停止等待")
                break

        # 关闭连接
        await websocket.close()
        print()
        print("="*60)
        print("🔌 连接已关闭")
        print("="*60)

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(demo())