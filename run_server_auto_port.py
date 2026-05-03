"""
FastAPI WebSocket 服务器启动脚本 - 自动选择可用端口
"""
import sys
import os
import socket

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json
import time
import numpy as np
import logging

from src.config import settings
from src.websocket.connection_manager import ConnectionManager
from src.models.messages import TextInputMessage, ControlMessage
from src.vad.vad_monitor import VADMonitor
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException
from src.llm.llm_router import LLMRouter
from src.models.llm_config import LLMConfig
from src.state.session_manager import SessionManager
from src.utils.audio_utils import convert_to_float32
from src.dialogue.dialogue_manager import DialogueManager
from src.api.character_routes import setup_character_routes
from src.api.voice_routes import setup_voice_routes
from src.state.storage import init_database

logger = logging.getLogger(__name__)

app = FastAPI(title="Real-time Voice Narrative System")

# CORS - 允许前端跨域访问
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 REST API 路由
setup_character_routes(app)
setup_voice_routes(app)

# 全局管理器
manager = ConnectionManager()
session_manager = SessionManager()

# 全局 VAD 监控器
vad_monitor = VADMonitor(
    sample_rate=settings.VAD_SAMPLE_RATE,
    threshold=settings.VAD_THRESHOLD
)

# 会话级别的处理器
interrupt_handlers = {}
dialogue_managers = {}  # 使用对话管理器替代单独的llm_routers和tts_streamers


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    init_database()
    await session_manager.initialize()
    logger.info("Server started")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    await session_manager.shutdown()
    logger.info("Server shutdown")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 端点 - 使用对话管理器"""
    await manager.connect(websocket, session_id)

    # 初始化会话处理器
    interrupt_handlers[session_id] = InterruptHandler()

    # 初始化对话管理器
    try:
        dialogue_managers[session_id] = DialogueManager(
            character_name="童锦程",  # 默认角色
            enable_memory=True,
            enable_emotion=True,
            enable_tts=True
        )
        logger.info(f"[Session {session_id}] Dialogue manager initialized")
    except Exception as e:
        logger.error(f"[Session {session_id}] Failed to initialize dialogue manager: {e}")
        await manager.send_error(session_id, "INIT_ERROR", str(e), recoverable=False)
        return

    try:
        async def heartbeat():
            while True:
                try:
                    await asyncio.sleep(30)
                    if session_id in manager.active_connections:
                        await manager.send_json(session_id, {"type": "heartbeat"})
                except:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        while True:
            raw_message = await websocket.receive()

            if "text" in raw_message:
                message_data = json.loads(raw_message["text"])
                message_type = message_data.get("type")

                if message_type == "text_input":
                    message = TextInputMessage(**message_data)
                    await handle_text_input(session_id, message)
                elif message_type == "control":
                    message = ControlMessage(**message_data)
                    await handle_control(session_id, message)
                elif message_type == "switch_character":
                    dialogue = dialogue_managers.get(session_id)
                    if dialogue:
                        success = dialogue.switch_character(message_data.get("character_name", ""))
                        await manager.send_json(session_id, {
                            "type": "character_switched",
                            "success": success,
                            "character_name": message_data.get("character_name")
                        })
                        if success:
                            info = dialogue.get_character_info()
                            await manager.send_json(session_id, {
                                "type": "character_info",
                                **info
                            })
                elif message_type == "list_characters":
                    dialogue = dialogue_managers.get(session_id)
                    if dialogue:
                        char_list = list(dialogue.character_manager.cards.keys())
                        await manager.send_json(session_id, {
                            "type": "character_list",
                            "characters": char_list
                        })

            elif "bytes" in raw_message:
                audio_data = raw_message["bytes"]
                await handle_audio_input(session_id, audio_data)

    except WebSocketDisconnect:
        heartbeat_task.cancel()
        cleanup_session(session_id)
        logger.info(f"Session {session_id} disconnected normally")
    except Exception as e:
        heartbeat_task.cancel()
        logger.error(f"Session {session_id} error: {e}")
        # 只在连接仍然活跃时发送错误消息
        if manager.is_connected(session_id):
            try:
                await manager.send_error(session_id, "CONNECTION_ERROR", str(e), recoverable=False)
            except Exception:
                pass  # 忽略发送错误
        cleanup_session(session_id)


async def handle_text_input(session_id: str, message: TextInputMessage):
    """处理文本输入 - 使用对话管理器，支持 /switch 等命令"""
    content = message.content.strip()
    logger.info(f"[Session {session_id}] Text input: {content}")

    state = manager.get_session_state(session_id)
    if state:
        state.update_activity()

    # 检查文本命令
    if content.startswith("/"):
        await handle_text_command(session_id, content)
        return

    await manager.send_status(session_id, "processing")

    try:
        if session_id in dialogue_managers:
            dialogue = dialogue_managers[session_id]

            first_audio_chunk = True
            async for msg in dialogue.chat(content, return_audio=True):
                if msg["type"] == "emotion":
                    await manager.send_json(session_id, {
                        "type": "emotion",
                        "emotion": msg["emotion"],
                        "intensity": msg["intensity"]
                    })

                elif msg["type"] == "text_chunk":
                    await manager.send_text_chunk(
                        session_id,
                        msg["content"],
                        is_final=msg["is_final"]
                    )

                elif msg["type"] == "audio":
                    if msg["data"]:
                        await manager.send_audio(
                            session_id, msg["data"],
                            is_new_file=first_audio_chunk,
                            format=msg.get("format", "mp3"),
                            is_final=msg["is_final"]
                        )
                        first_audio_chunk = False
                    elif msg["is_final"]:
                        await manager.send_audio(
                            session_id, b"",
                            is_new_file=False,
                            format=msg.get("format", "mp3"),
                            is_final=True
                        )

                elif msg["type"] == "complete":
                    logger.info(f"[Session {session_id}] Dialogue completed")

                elif msg["type"] == "error":
                    await manager.send_error(
                        session_id,
                        "DIALOGUE_ERROR",
                        msg["message"],
                        recoverable=True
                    )

        else:
            await asyncio.sleep(0.5)
            await manager.send_text_chunk(
                session_id,
                f"收到: {content}",
                is_final=True
            )

        await manager.send_status(session_id, "listening")
    except VADInterruptException:
        logger.info(f"[Session {session_id}] Generation interrupted")
        await manager.send_status(session_id, "listening")
    except Exception as e:
        logger.error(f"[Session {session_id}] Text processing error: {e}")
        await manager.send_error(session_id, "PROCESSING_ERROR", str(e), recoverable=True)
        await manager.send_status(session_id, "listening")


async def handle_text_command(session_id: str, content: str):
    """处理文本中以 / 开头的命令"""
    parts = content.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    dialogue = dialogue_managers.get(session_id)
    if not dialogue:
        await manager.send_text_chunk(session_id, "系统未初始化", is_final=True)
        return

    if cmd == "/switch" and arg:
        success = dialogue.switch_character(arg)
        if success:
            info = dialogue.get_character_info()
            await manager.send_json(session_id, {
                "type": "character_switched",
                "success": True,
                "character_name": arg
            })
            await manager.send_json(session_id, {
                "type": "character_info",
                **info
            })
            await manager.send_text_chunk(
                session_id,
                f"已切换为 {arg}。{dialogue.character.first_mes}",
                is_final=True
            )
        else:
            chars = dialogue.character_manager.list_cards()
            await manager.send_text_chunk(
                session_id,
                f"角色 '{arg}' 不存在。可用角色: {', '.join(chars)}",
                is_final=True
            )

    elif cmd == "/characters":
        chars = dialogue.character_manager.list_cards()
        current = dialogue.character.name
        char_list = "\n".join(f"{'→ ' if c == current else '   '}{c}" for c in chars)
        await manager.send_text_chunk(
            session_id,
            f"可用角色:\n{char_list}\n\n输入 /switch <角色名> 切换",
            is_final=True
        )
        await manager.send_json(session_id, {
            "type": "character_list",
            "characters": chars,
            "current": current
        })

    elif cmd == "/voice" and arg:
        from src.tts.voice_profile_manager import VoiceProfileManager
        vpm = VoiceProfileManager()
        profile = vpm.get_profile(arg)
        if profile:
            dialogue.voice_profile = profile
            await manager.send_text_chunk(
                session_id,
                f"已切换声音为 {arg}: {profile.get('description', '')}",
                is_final=True
            )
        else:
            voices = vpm.list_profiles()
            await manager.send_text_chunk(
                session_id,
                f"声音 '{arg}' 不存在。可用: {', '.join(voices)}",
                is_final=True
            )

    elif cmd == "/voices":
        from src.tts.voice_profile_manager import VoiceProfileManager
        vpm = VoiceProfileManager()
        voices = vpm.list_profiles()
        current = getattr(dialogue, 'voice_profile', {}).get('name', 'default')
        voice_list = "\n".join(f"{'→ ' if v == current else '   '}{v}" for v in voices)
        await manager.send_text_chunk(
            session_id,
            f"可用声音:\n{voice_list}\n\n输入 /voice <声音名> 切换",
            is_final=True
        )

    elif cmd == "/info":
        info = dialogue.get_character_info()
        voice_info = getattr(dialogue, 'voice_profile', {})
        await manager.send_text_chunk(
            session_id,
            f"当前角色: {info['name']}\n描述: {info['description']}\n性格: {info['personality']}\n声音: {voice_info.get('name', '默认')}",
            is_final=True
        )

    elif cmd == "/help":
        await manager.send_text_chunk(
            session_id,
            "命令列表:\n"
            "/switch <角色名> - 切换AI人格\n"
            "/characters - 列出所有角色\n"
            "/voice <声音名> - 切换声音\n"
            "/voices - 列出所有可用声音\n"
            "/info - 显示当前状态\n"
            "/clear - 清空对话记忆\n"
            "/help - 显示此帮助",
            is_final=True
        )

    elif cmd == "/clear":
        dialogue.clear_conversation()
        await manager.send_text_chunk(
            session_id,
            "对话记忆已清空。",
            is_final=True
        )

    else:
        await manager.send_text_chunk(
            session_id,
            f"未知命令: {cmd}。输入 /help 查看可用命令。",
            is_final=True
        )

    await manager.send_status(session_id, "listening")


async def handle_audio_input(session_id: str, audio_data: bytes):
    """处理音频输入 - 期望原始PCM int16格式"""
    state = manager.get_session_state(session_id)
    if state:
        state.total_audio_received += len(audio_data)

    try:
        # VAD expects raw PCM int16; webm/opus from browser won't decode correctly here
        if len(audio_data) < 2 or len(audio_data) % 2 != 0:
            return
        audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
        audio_float32 = convert_to_float32(audio_int16)
        is_speech = vad_monitor.detect_speech(audio_float32)

        await manager.send_json(session_id, {
            "type": "vad_status",
            "is_speech": is_speech,
            "timestamp": time.time()
        })

        if is_speech:
            interrupt_handler = interrupt_handlers.get(session_id)
            if interrupt_handler:
                interrupt_handler.trigger_interrupt()
                logger.info(f"[Session {session_id}] VAD detected speech")
    except Exception as e:
        logger.error(f"[Session {session_id}] Audio processing error: {e}")


async def handle_control(session_id: str, message: ControlMessage):
    """处理控制消息"""
    logger.info(f"[Session {session_id}] Control: {message.action}")
    interrupt_handler = interrupt_handlers.get(session_id)

    if message.action == "interrupt":
        if interrupt_handler:
            interrupt_handler.trigger_interrupt()
        await manager.send_status(session_id, "listening")
    elif message.action == "pause":
        await manager.send_status(session_id, "idle")
    elif message.action == "resume":
        if interrupt_handler:
            interrupt_handler.clear_interrupt()
        await manager.send_status(session_id, "listening")
    elif message.action == "stop":
        await manager.send_status(session_id, "idle")


def cleanup_session(session_id: str):
    """清理会话资源"""
    manager.disconnect(session_id)
    if session_id in interrupt_handlers:
        del interrupt_handlers[session_id]
    if session_id in dialogue_managers:
        del dialogue_managers[session_id]
    logger.info(f"[Session {session_id}] Resources cleaned up")


def find_available_port(start_port=8000, max_attempts=100):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)

    # 默认 8765 端口，可通过环境变量覆盖
    PORT = int(os.environ.get("SERVER_PORT", "8765"))

    print("=" * 60)
    print("Real-time Voice Narrative System")
    print("=" * 60)
    print()
    print(f"Server:         http://localhost:{PORT}")
    print(f"API Docs:       http://localhost:{PORT}/docs")
    print(f"WebSocket:      ws://localhost:{PORT}/ws/{{session_id}}")
    print(f"Characters API: http://localhost:{PORT}/api/characters/")
    print(f"Voice API:      http://localhost:{PORT}/api/voice/profiles")
    print()
    print("Commands in chat:")
    print("  /switch <name>   - Switch AI personality")
    print("  /characters      - List characters")
    print("  /voice <name>    - Switch voice")
    print("  /voices          - List voices")
    print("  /help            - Show all commands")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
    except OSError as e:
        print(f"ERROR: Port {PORT} is already in use: {e}")
        sys.exit(1)