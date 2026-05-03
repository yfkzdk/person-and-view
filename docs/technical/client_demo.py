"""
WebSocket 客户端 - 用于测试实时语音叙事系统
"""
import asyncio
import websockets
import json
import base64
import numpy as np
from datetime import datetime


class VoiceNarrativeClient:
    """实时语音叙事系统客户端"""

    def __init__(self, server_url: str = "ws://localhost:8000/ws/demo-session"):
        self.server_url = server_url
        self.session_id = "demo-session"
        self.websocket = None  # 初始化 websocket 属性
        self._audio_count = 0
        self._audio_total_bytes = 0
        self._current_audio_index = 0
        self._audio_files = []  # 记录所有音频文件

    async def connect(self):
        """连接到服务器"""
        print(f"🔗 正在连接到 {self.server_url}...")
        self.websocket = await websockets.connect(self.server_url)
        print("✅ 连接成功！")

        # 接收初始状态
        initial_status = await self.receive_message()
        print(f"📊 初始状态: {initial_status}")

    async def send_text(self, content: str):
        """发送文本消息"""
        message = {
            "type": "text_input",
            "content": content,
            "session_id": self.session_id
        }
        await self.websocket.send(json.dumps(message))
        print(f"📤 发送文本: {content}")

    async def send_audio(self, audio_data: bytes):
        """发送音频数据"""
        await self.websocket.send(audio_data)
        print(f"📤 发送音频: {len(audio_data)} bytes")

    async def send_control(self, action: str):
        """发送控制指令"""
        message = {
            "type": "control",
            "action": action,
            "session_id": self.session_id
        }
        await self.websocket.send(json.dumps(message))
        print(f"📤 发送控制: {action}")

    async def receive_message(self):
        """接收消息"""
        raw_message = await self.websocket.recv()

        try:
            # 尝试解析 JSON
            message = json.loads(raw_message)
            return message
        except json.JSONDecodeError:
            # 如果不是 JSON，可能是二进制音频
            print(f"📥 接收二进制数据: {len(raw_message)} bytes")
            return {"type": "binary", "data": raw_message}

    async def listen_for_responses(self, timeout: float = 30.0):
        """监听服务器响应"""
        print("🎧 开始监听服务器响应...")
        start_time = datetime.now()

        while True:
            try:
                # 检查超时
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    print(f"⏱️ 监听超时 ({timeout}秒)")
                    break

                # 接收消息
                message = await asyncio.wait_for(
                    self.receive_message(),
                    timeout=5.0
                )

                # 处理不同类型的消息
                msg_type = message.get("type", "unknown")

                if msg_type == "status":
                    status = message.get("status", "unknown")
                    print(f"📊 状态更新: {status}")

                    # 如果状态回到 listening，表示处理完成
                    if status == "listening":
                        # 显示最后一个音频文件的汇总
                        if self._audio_count > 0:
                            print(f"🔊 音频 {self._current_audio_index} 完成: {self._audio_count} 块, {self._audio_total_bytes} bytes")

                        if len(self._audio_files) > 0:
                            print(f"💾 本次对话生成了 {len(self._audio_files)} 个音频文件:")
                            for filename in self._audio_files:
                                print(f"   - {filename}")

                        print("✅ 处理完成，系统回到监听状态")

                        # 清空计数器，准备下一次对话
                        self._audio_count = 0
                        self._audio_total_bytes = 0
                        self._audio_files = []

                        break

                elif msg_type == "text_chunk":
                    content = message.get("content", "")
                    is_final = message.get("is_final", False)

                    if content:
                        # 实时输出文本，不换行
                        print(content, end="", flush=True)

                    if is_final:
                        print()  # 文本生成完成后换行
                        print("✅ 文本生成完成")

                elif msg_type == "audio":
                    audio_data = message.get("data", "")
                    audio_index = message.get("audio_index", 0)
                    is_new_file = message.get("is_new_file", False)

                    if audio_data:
                        # 解码 base64 音频
                        audio_bytes = base64.b64decode(audio_data)

                        # 如果是新文件，创建新的文件名
                        if is_new_file:
                            if self._current_audio_index > 0:
                                # 显示上一个文件的汇总
                                print(f"🔊 音频 {self._current_audio_index} 完成: {self._audio_count} 块, {self._audio_total_bytes} bytes")

                            # 开始新文件
                            self._current_audio_index = audio_index
                            self._audio_count = 0
                            self._audio_total_bytes = 0
                            audio_filename = f"output_audio_{audio_index}.wav"
                            self._audio_files.append(audio_filename)
                            print(f"💾 开始保存音频文件: {audio_filename}")

                        self._audio_count += 1
                        self._audio_total_bytes += len(audio_bytes)

                        # 保存音频文件
                        audio_filename = f"output_audio_{self._current_audio_index}.wav"
                        with open(audio_filename, "ab") as f:
                            f.write(audio_bytes)

                elif msg_type == "vad_status":
                    is_speech = message.get("is_speech", False)
                    print(f"🎤 VAD 检测: {'语音' if is_speech else '静音'}")

                elif msg_type == "error":
                    error_code = message.get("error_code", "unknown")
                    error_msg = message.get("message", "unknown error")
                    print(f"❌ 错误: [{error_code}] {error_msg}")

                else:
                    print(f"📥 未知消息类型: {msg_type}")
                    print(f"   内容: {message}")

            except asyncio.TimeoutError:
                print("⏱️ 5秒内无消息，继续监听...")
                continue

            except Exception as e:
                print(f"❌ 监听错误: {e}")
                break

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 连接已关闭")


async def demo_text_interaction():
    """演示文本交互"""
    print("\n" + "="*60)
    print("📝 文本交互演示")
    print("="*60)

    client = VoiceNarrativeClient()

    try:
        # 连接服务器
        await client.connect()

        # 发送文本消息
        await client.send_text("你好，请介绍一下你自己")

        # 监听响应
        await client.listen_for_responses(timeout=30.0)

    finally:
        await client.close()


async def demo_interrupt_flow():
    """演示打断流程"""
    print("\n" + "="*60)
    print("⚡ 打断流程演示")
    print("="*60)

    client = VoiceNarrativeClient()

    try:
        # 连接服务器
        await client.connect()

        # 发送文本消息
        await client.send_text("请讲一个很长的故事")

        # 等待 2 秒后打断
        await asyncio.sleep(2)
        print("⏱️ 2秒后发送打断指令...")

        # 发送打断指令
        await client.send_control("interrupt")

        # 监听响应
        await client.listen_for_responses(timeout=10.0)

    finally:
        await client.close()


async def demo_pause_resume():
    """演示暂停和恢复"""
    print("\n" + "="*60)
    print("⏸️ 暂停恢复演示")
    print("="*60)

    client = VoiceNarrativeClient()

    try:
        # 连接服务器
        await client.connect()

        # 发送暂停指令
        await client.send_control("pause")
        await client.listen_for_responses(timeout=5.0)

        # 等待 3 秒
        await asyncio.sleep(3)
        print("⏱️ 3秒后恢复...")

        # 发送恢复指令
        await client.send_control("resume")
        await client.listen_for_responses(timeout=5.0)

    finally:
        await client.close()


async def demo_audio_input():
    """演示音频输入"""
    print("\n" + "="*60)
    print("🎤 音频输入演示")
    print("="*60)

    client = VoiceNarrativeClient()

    try:
        # 连接服务器
        await client.connect()

        # 生成模拟音频数据（512 samples = 1024 bytes for int16）
        # 实际使用时，应该从麦克风录制真实音频
        audio_samples = np.random.randint(-1000, 1000, size=512, dtype=np.int16)
        audio_data = audio_samples.tobytes()

        print(f"🎤 发送模拟音频数据 ({len(audio_data)} bytes)")
        await client.send_audio(audio_data)

        # 监听 VAD 检测结果
        await client.listen_for_responses(timeout=5.0)

    finally:
        await client.close()


async def interactive_mode():
    """交互模式 - 用户可以自由输入"""
    print("\n" + "="*60)
    print("🎮 交互模式")
    print("="*60)
    print("可用命令:")
    print("  - 输入任意文本进行对话")
    print("  - 'interrupt' - 打断当前生成")
    print("  - 'pause' - 暂停系统")
    print("  - 'resume' - 恢复系统")
    print("  - 'audio' - 发送模拟音频")
    print("  - 'quit' - 退出程序")
    print("="*60)

    client = VoiceNarrativeClient()

    try:
        # 连接服务器
        await client.connect()

        while True:
            # 获取用户输入
            user_input = input("\n💬 请输入: ").strip()

            if not user_input:
                continue

            # 处理特殊命令
            if user_input.lower() == "quit":
                print("👋 退出程序")
                break

            elif user_input.lower() == "interrupt":
                await client.send_control("interrupt")
                await client.listen_for_responses(timeout=5.0)

            elif user_input.lower() == "pause":
                await client.send_control("pause")
                await client.listen_for_responses(timeout=5.0)

            elif user_input.lower() == "resume":
                await client.send_control("resume")
                await client.listen_for_responses(timeout=5.0)

            elif user_input.lower() == "audio":
                # 发送模拟音频
                audio_samples = np.random.randint(-1000, 1000, size=512, dtype=np.int16)
                audio_data = audio_samples.tobytes()
                await client.send_audio(audio_data)
                await client.listen_for_responses(timeout=5.0)

            else:
                # 发送文本消息
                await client.send_text(user_input)
                await client.listen_for_responses(timeout=30.0)

    finally:
        await client.close()


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("🎙️ 实时语音叙事系统 - 客户端演示")
    print("="*60)
    print("\n请选择演示模式:")
    print("1. 文本交互演示")
    print("2. 打断流程演示")
    print("3. 暂停恢复演示")
    print("4. 音频输入演示")
    print("5. 交互模式（推荐）")
    print("="*60)

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == "1":
        await demo_text_interaction()

    elif choice == "2":
        await demo_interrupt_flow()

    elif choice == "3":
        await demo_pause_resume()

    elif choice == "4":
        await demo_audio_input()

    elif choice == "5":
        await interactive_mode()

    else:
        print("❌ 无效选项，启动交互模式...")
        await interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")