"""
FastAPI WebSocket 服务器 - 完整集成版本
使用 DialogueManager 统一编排所有组件
"""
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import asyncio
import json
import time
import copy
import numpy as np
import logging

from src.config import settings
from src.websocket.connection_manager import ConnectionManager
from src.models.messages import TextInputMessage, ControlMessage
from src.vad.vad_monitor import VADMonitor
from src.vad.interrupt_handler import InterruptHandler, VADInterruptException
from src.state.session_manager import SessionManager
from src.utils.audio_utils import convert_to_float32
from src.memory.knowledge_graph import KnowledgeGraph, MultiKnowledgeGraph
from src.dialogue.dialogue_manager import DialogueManager
from src.memory.evolution_engine import (
    run_evolution_cycle, confirm_candidate, reject_candidate,
    get_evolution_status, cleanup_evolution_nodes
)
from src.api.character_routes import setup_character_routes
from src.api.voice_routes import setup_voice_routes

logger = logging.getLogger(__name__)

app = FastAPI(title="Real-time Voice Narrative System")

# CORS
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

# 静态文件 - 替代前端 (testsss3.html)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend_alt"
frontend_dir.mkdir(exist_ok=True)
app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_alt")

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
dialogue_managers = {}

# 会话级别的动态设置
session_settings: dict = {}

# 会话级别的知识图谱实例
session_knowledge_graphs: dict = {}

DEFAULT_SETTINGS = {
    "character": {
        "persona_depth": 1.0,
        "temperature": 0.7,
        "response_length": "medium",
        "creativity": 0.5
    },
    "memory": {
        "retrieval_count": 2,
        "relevance_threshold": 0.0,
        "context_chars": 600,
        "history_window": 30
    },
    "voice": {
        "speed": 1.0,
        "pitch": 0,
        "voice_id": "default"
    },
    "knowledge": {
        "enabled_nodes": [],
        "disabled_nodes": [],
        "use_multi_kg": True
    }
}


def get_session_settings(session_id: str) -> dict:
    """获取会话设置，首次访问返回默认值。"""
    if session_id not in session_settings:
        session_settings[session_id] = copy.deepcopy(DEFAULT_SETTINGS)
    return session_settings[session_id]


def deep_merge(base: dict, update: dict):
    """递归合并设置。"""
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    await session_manager.initialize()
    logger.info("Server started")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    await session_manager.shutdown()
    logger.info("Server shutdown")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 端点"""
    await manager.connect(websocket, session_id)

    # 初始化会话处理器
    interrupt_handlers[session_id] = InterruptHandler()

    # 初始化对话管理器
    try:
        session_cfg = get_session_settings(session_id)
        use_multi_kg = session_cfg.get("knowledge", {}).get("use_multi_kg", True)
        dialogue_managers[session_id] = DialogueManager(
            character_name="童锦程",
            enable_memory=True,
            enable_emotion=True,
            enable_tts=True,
            use_multi_kg=use_multi_kg
        )
        logger.info(f"[Session {session_id}] Dialogue manager initialized with character switching and voice support")
    except Exception as e:
        logger.error(f"[Session {session_id}] Failed to initialize dialogue manager: {e}")
        await manager.send_error(session_id, "INIT_ERROR", str(e), recoverable=False)
        return

    try:
        # 心跳任务
        async def heartbeat():
            """发送心跳保持连接"""
            while True:
                try:
                    await asyncio.sleep(30)  # 每30秒发送一次心跳
                    if session_id in manager.active_connections:
                        await manager.send_json(session_id, {"type": "heartbeat"})
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        while True:
            # 接收消息
            raw_message = await websocket.receive()

            # 处理文本消息
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

            # 处理二进制消息（音频）
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
        await manager.send_error(
            session_id,
            "CONNECTION_ERROR",
            str(e),
            recoverable=False
        )
        cleanup_session(session_id)


async def handle_text_input(session_id: str, message: TextInputMessage):
    """处理文本输入 - 使用 DialogueManager 统一编排"""
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
            settings = get_session_settings(session_id)
            async for msg in dialogue.chat(content, return_audio=True, interrupt_handler=interrupt_handlers.get(session_id), settings=settings):
                if msg["type"] == "interrupted":
                    await manager.send_json(session_id, {"type": "interrupted"})
                    break
                elif msg["type"] == "emotion":
                    await manager.send_json(session_id, {
                        "type": "emotion",
                        "emotion": msg["emotion"],
                        "intensity": msg["intensity"],
                        "weights": msg.get("weights", {})
                    })
                elif msg["type"] == "text_chunk":
                    await manager.send_text_chunk(session_id, msg["content"], is_final=msg["is_final"])
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
                        await manager.send_audio(session_id, b"", is_new_file=False,
                                                 format=msg.get("format", "mp3"), is_final=True)
                elif msg["type"] == "error":
                    await manager.send_error(session_id, "DIALOGUE_ERROR", msg["message"], recoverable=True)
        else:
            await asyncio.sleep(0.5)
            await manager.send_text_chunk(session_id, f"收到: {content}", is_final=True)

        await manager.send_status(session_id, "listening")
    except VADInterruptException:
        logger.info(f"[Session {session_id}] Generation interrupted")
        await manager.send_status(session_id, "listening")
    except Exception as e:
        logger.error(f"[Session {session_id}] Text processing error: {e}")
        await manager.send_error(session_id, "PROCESSING_ERROR", str(e), recoverable=True)
        await manager.send_status(session_id, "listening")


async def handle_text_command(session_id: str, content: str):
    """处理文本命令"""
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
            await manager.send_json(session_id, {"type": "character_switched", "success": True, "character_name": arg})
            await manager.send_json(session_id, {"type": "character_info", **info})
            await manager.send_text_chunk(session_id, f"已切换为 {arg}。{dialogue.character.first_mes}", is_final=True)
        else:
            chars = dialogue.character_manager.list_cards()
            await manager.send_text_chunk(session_id, f"角色 '{arg}' 不存在。可用: {', '.join(chars)}", is_final=True)

    elif cmd == "/characters":
        chars = dialogue.character_manager.list_cards()
        current = dialogue.character.name
        char_list = "\n".join(f"{'→ ' if c == current else '   '}{c}" for c in chars)
        await manager.send_text_chunk(session_id, f"可用角色:\n{char_list}", is_final=True)
        await manager.send_json(session_id, {"type": "character_list", "characters": chars, "current": current})

    elif cmd == "/voice" and arg:
        from src.tts.voice_profile_manager import VoiceProfileManager
        vpm = VoiceProfileManager()
        profile = vpm.get_profile(arg)
        if profile:
            dialogue.voice_profile = profile
            await manager.send_text_chunk(session_id, f"已切换声音为 {arg}", is_final=True)
        else:
            voices = vpm.list_profiles()
            await manager.send_text_chunk(session_id, f"声音 '{arg}' 不存在。可用: {', '.join(voices)}", is_final=True)

    elif cmd == "/voices":
        from src.tts.voice_profile_manager import VoiceProfileManager
        vpm = VoiceProfileManager()
        voices = vpm.list_profiles()
        await manager.send_text_chunk(session_id, f"可用声音: {', '.join(voices)}", is_final=True)

    elif cmd == "/help":
        await manager.send_text_chunk(session_id,
            "命令: /switch <角色名> | /characters | /voice <声音名> | /voices | /clear | /help", is_final=True)

    elif cmd == "/clear":
        dialogue.clear_conversation()
        await manager.send_text_chunk(session_id, "对话记忆已清空。", is_final=True)

    else:
        await manager.send_text_chunk(session_id, f"未知命令: {cmd}。输入 /help 查看可用命令。", is_final=True)

    await manager.send_status(session_id, "listening")


async def handle_audio_input(session_id: str, audio_data: bytes):
    """处理音频输入 - VAD 检测"""
    # 更新统计
    state = manager.get_session_state(session_id)
    if state:
        state.total_audio_received += len(audio_data)

    try:
        # 转换音频格式
        audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
        audio_float32 = convert_to_float32(audio_int16)

        # VAD 检测
        is_speech = vad_monitor.detect_speech(audio_float32)

        # 发送 VAD 状态
        await manager.send_json(session_id, {
            "type": "vad_status",
            "is_speech": is_speech,
            "timestamp": time.time()
        })

        # 如果检测到语音，触发打断
        if is_speech:
            interrupt_handler = interrupt_handlers.get(session_id)
            if interrupt_handler:
                interrupt_handler.trigger_interrupt()
                logger.info(f"[Session {session_id}] VAD detected speech, interrupt triggered")

    except Exception as e:
        logger.error(f"[Session {session_id}] Audio processing error: {e}")


async def handle_control(session_id: str, message: ControlMessage):
    """处理控制消息 - 打断逻辑"""
    logger.info(f"[Session {session_id}] Control: {message.action}")

    interrupt_handler = interrupt_handlers.get(session_id)

    if message.action == "interrupt":
        # 触发打断
        if interrupt_handler:
            interrupt_handler.trigger_interrupt()

        # 取消正在进行的任务
        # TODO: 实现任务取消逻辑（需要追踪当前任务）

        await manager.send_status(session_id, "listening")

    elif message.action == "pause":
        await manager.send_status(session_id, "idle")

    elif message.action == "resume":
        # 清除打断状态
        if interrupt_handler:
            interrupt_handler.clear_interrupt()

        await manager.send_status(session_id, "listening")

    elif message.action == "stop":
        await manager.send_status(session_id, "idle")


# ==================== REST API — 设置面板 ====================

@app.get("/api/settings")
async def api_get_settings(session_id: str = "default"):
    """获取当前会话的设置。"""
    return JSONResponse(get_session_settings(session_id))


@app.post("/api/settings")
async def api_update_settings(session_id: str = "default", body: dict = Body(None)):
    """更新会话设置。前端设置面板调用此接口保存用户调整。"""
    if not body:
        return JSONResponse({"error": "empty body"}, status_code=400)
    current = get_session_settings(session_id)
    deep_merge(current, body)
    logger.info(f"[Settings] Updated settings for session {session_id}: {list(body.keys())}")
    return JSONResponse({"status": "ok", "settings": current})


@app.get("/api/knowledge-graph/{character_name}")
async def api_get_knowledge_graph(character_name: str, session_id: str = "default"):
    """获取角色的知识图谱数据（供前端网状可视化渲染）。"""
    if session_id not in session_knowledge_graphs:
        session_knowledge_graphs[session_id] = KnowledgeGraph(character_name)
    kg = session_knowledge_graphs[session_id]
    # 同步 disabled 节点状态
    settings = get_session_settings(session_id)
    disabled = settings.get("knowledge", {}).get("disabled_nodes", [])
    if disabled:
        kg.set_disabled_nodes(disabled)
    return JSONResponse(kg.to_dict())


@app.post("/api/knowledge-graph/{character_name}/toggle")
async def api_toggle_knowledge_node(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """手动开关知识图谱节点。"""
    if not body or "node_id" not in body or "enabled" not in body:
        return JSONResponse({"error": "need node_id and enabled"}, status_code=400)

    if session_id not in session_knowledge_graphs:
        session_knowledge_graphs[session_id] = KnowledgeGraph(character_name)

    kg = session_knowledge_graphs[session_id]
    kg.toggle_node(body["node_id"], body["enabled"])

    # 同步回设置
    settings = get_session_settings(session_id)
    settings["knowledge"]["disabled_nodes"] = kg.get_disabled_nodes()

    return JSONResponse({"status": "ok", "disabled_nodes": kg.get_disabled_nodes()})


# ==================== 知识图谱 CRUD 编辑 API ====================

def _get_or_create_kg(character_name: str, session_id: str) -> KnowledgeGraph:
    """获取或创建会话级知识图谱实例。"""
    if session_id not in session_knowledge_graphs:
        session_knowledge_graphs[session_id] = KnowledgeGraph(character_name)
    return session_knowledge_graphs[session_id]


@app.post("/api/knowledge-graph/{character_name}/nodes")
async def api_upsert_knowledge_node(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """添加或更新知识图谱节点。body: {id?, label, type, summary, content, triggers, tags}"""
    if not body or "label" not in body:
        return JSONResponse({"error": "need at least 'label'"}, status_code=400)
    kg = _get_or_create_kg(character_name, session_id)
    try:
        node = kg.upsert_node(body)
        return JSONResponse({"status": "ok", "node": {
            "id": node.id, "type": node.type, "label": node.label,
            "summary": node.summary, "content": node.content,
            "triggers": node.triggers, "tags": node.tags
        }})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/knowledge-graph/{character_name}/nodes/{node_id}")
async def api_delete_knowledge_node(character_name: str, node_id: str, session_id: str = "default"):
    """删除知识图谱节点。"""
    kg = _get_or_create_kg(character_name, session_id)
    ok = kg.delete_node(node_id)
    if not ok:
        return JSONResponse({"error": "node not found"}, status_code=404)
    return JSONResponse({"status": "ok", "deleted": node_id})


@app.post("/api/knowledge-graph/{character_name}/edges")
async def api_upsert_knowledge_edge(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """添加或更新知识图谱边。body: {source, target, relation, description?}"""
    if not body or "source" not in body or "target" not in body:
        return JSONResponse({"error": "need source and target"}, status_code=400)
    kg = _get_or_create_kg(character_name, session_id)
    try:
        edge = kg.upsert_edge(body)
        return JSONResponse({"status": "ok", "edge": {
            "source": edge.source, "target": edge.target,
            "relation": edge.relation, "description": edge.description
        }})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.delete("/api/knowledge-graph/{character_name}/edges")
async def api_delete_knowledge_edge(character_name: str, session_id: str = "default", body: dict = None):
    """删除知识图谱边。body: {source, target}"""
    if not body or "source" not in body or "target" not in body:
        return JSONResponse({"error": "need source and target"}, status_code=400)
    kg = _get_or_create_kg(character_name, session_id)
    ok = kg.delete_edge(body["source"], body["target"])
    if not ok:
        return JSONResponse({"error": "edge not found"}, status_code=404)
    return JSONResponse({"status": "ok", "deleted": f"{body['source']} -> {body['target']}"})


# ==================== 多图谱聚合 API ====================

session_multi_kgs: dict = {}


def _get_or_create_multi_kg(character_name: str, session_id: str) -> MultiKnowledgeGraph:
    if session_id not in session_multi_kgs:
        session_multi_kgs[session_id] = MultiKnowledgeGraph(character_name)
    return session_multi_kgs[session_id]


@app.get("/api/knowledge-graph/multi/{character_name}")
async def api_get_multi_knowledge_graph(character_name: str, session_id: str = "default"):
    """获取角色的多图谱聚合数据，含 per-graph 配置和禁用状态。"""
    mkg = _get_or_create_multi_kg(character_name, session_id)
    settings = get_session_settings(session_id)
    disabled = settings.get("knowledge", {}).get("disabled_nodes", [])
    if disabled:
        mkg.set_disabled_nodes(disabled)
    saved_configs = settings.get("knowledge", {}).get("graph_configs", {})
    if saved_configs:
        mkg.set_all_configs(saved_configs)
    return JSONResponse(mkg.to_dict())


@app.post("/api/knowledge-graph/multi/{character_name}/toggle")
async def api_toggle_multi_node(character_name: str, session_id: str = "default", body: dict = Body(None)):
    if not body or "node_id" not in body or "enabled" not in body:
        return JSONResponse({"error": "need node_id and enabled"}, status_code=400)
    mkg = _get_or_create_multi_kg(character_name, session_id)
    mkg.toggle_node(body["node_id"], body["enabled"])
    settings = get_session_settings(session_id)
    settings["knowledge"]["disabled_nodes"] = mkg.get_disabled_nodes()
    return JSONResponse({"status": "ok", "disabled_nodes": mkg.get_disabled_nodes()})


@app.get("/api/knowledge-graph/multi/{character_name}/configs")
async def api_get_multi_configs(character_name: str, session_id: str = "default"):
    """获取所有子图谱的独立配置。"""
    mkg = _get_or_create_multi_kg(character_name, session_id)
    # 从 session settings 恢复
    settings = get_session_settings(session_id)
    saved_configs = settings.get("knowledge", {}).get("graph_configs", {})
    if saved_configs:
        mkg.set_all_configs(saved_configs)
    return JSONResponse({"configs": mkg.get_all_configs()})


@app.post("/api/knowledge-graph/multi/{character_name}/configs")
async def api_update_multi_configs(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """更新子图谱配置。body: {"configs": {"童锦程": {"persona_depth": 1.2}, ...}}"""
    if not body or "configs" not in body:
        return JSONResponse({"error": "need configs dict"}, status_code=400)
    mkg = _get_or_create_multi_kg(character_name, session_id)
    mkg.set_all_configs(body["configs"])
    # 持久化到 session settings
    settings = get_session_settings(session_id)
    if "knowledge" not in settings:
        settings["knowledge"] = {}
    settings["knowledge"]["graph_configs"] = mkg.get_all_configs()
    return JSONResponse({"status": "ok", "configs": mkg.get_all_configs()})


# ==================== 自进化 API ====================

@app.get("/api/evolution/{character_name}/status")
async def api_get_evolution_status(character_name: str, session_id: str = "default"):
    """获取进化状态：pending 候选、历史记录、健康状态。"""
    settings = get_session_settings(session_id)
    status = get_evolution_status(settings)
    return JSONResponse(status)


@app.post("/api/evolution/{character_name}/trigger")
async def api_trigger_evolution(character_name: str, session_id: str = "default"):
    """手动触发一轮进化检测（调试用）。"""
    settings = get_session_settings(session_id)
    mkg = _get_or_create_multi_kg(character_name, session_id) if session_id in session_multi_kgs else None
    all_nodes, all_edges = {}, []
    if mkg:
        all_nodes, all_edges = mkg.get_all_nodes_and_edges()

    result = run_evolution_cycle(
        settings=settings,
        character_name=character_name,
        force=True,
        existing_nodes=all_nodes,
        existing_edges=all_edges
    )
    return JSONResponse(result)


@app.post("/api/evolution/{character_name}/confirm")
async def api_confirm_evolution(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """
    确认一个候选节点，注入到知识图谱。
    body: {
        candidate_index: 0,
        custom_label?: str,
        custom_summary?: str,
        custom_triggers?: [str]
    }
    """
    if not body or "candidate_index" not in body:
        return JSONResponse({"error": "need candidate_index"}, status_code=400)

    settings = get_session_settings(session_id)

    try:
        confirmed = confirm_candidate(
            settings=settings,
            candidate_index=body["candidate_index"],
            custom_label=body.get("custom_label"),
            custom_summary=body.get("custom_summary"),
            custom_triggers=body.get("custom_triggers"),
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    # Inject into MultiKnowledgeGraph
    mkg = _get_or_create_multi_kg(character_name, session_id)
    node_data = confirmed["node"]
    edge_data = confirmed.get("edge")

    merge_target = node_data.pop("_merge_into", None)

    if merge_target:
        # Merge into existing node
        from src.memory.consistency_guard import merge_candidate_into_existing
        all_nodes, _ = mkg.get_all_nodes_and_edges()
        merged = merge_candidate_into_existing(node_data, merge_target, all_nodes)
        mkg.primary.upsert_node(merged)
        result_msg = f"merged into {merge_target}"
    else:
        # Create new node
        inserted = mkg.primary.upsert_node(node_data)
        result_msg = f"created node {inserted.id}"

        if edge_data:
            try:
                from src.memory.knowledge_graph import KGEdge
                src_id = KnowledgeGraph._sanitize_id(edge_data["source"])
                tgt_id = edge_data["target"]
                mkg.primary.upsert_edge({
                    "source": src_id,
                    "target": tgt_id,
                    "relation": edge_data.get("relation", "contradicts"),
                    "description": edge_data.get("description", "")
                })
                result_msg += f" + edge to {tgt_id}"
            except Exception as e:
                logger.warning(f"Edge creation failed: {e}")

    return JSONResponse({"status": "ok", "result": result_msg, "confirmed": confirmed})


@app.post("/api/evolution/{character_name}/reject")
async def api_reject_evolution(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """拒绝一个候选节点，该 gap 进入 30 轮冷却期。"""
    if not body or "candidate_index" not in body:
        return JSONResponse({"error": "need candidate_index"}, status_code=400)

    settings = get_session_settings(session_id)
    try:
        result = reject_candidate(settings, body["candidate_index"])
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    return JSONResponse({"status": "ok", "rejected": result["rejected"], "cooldown_turns": result["cooldown_turns"]})


@app.post("/api/evolution/{character_name}/cleanup")
async def api_cleanup_evolution(character_name: str, session_id: str = "default", body: dict = Body(None)):
    """清理进化历史节点。body: {keep_ids?: [str]} — 不传则清空全部。"""
    settings = get_session_settings(session_id)
    keep_ids = body.get("keep_ids") if body else None
    removed = cleanup_evolution_nodes(settings, keep_ids)
    return JSONResponse({"status": "ok", "removed": removed})


# ==================== 会话清理 ====================


def cleanup_session(session_id: str):
    """清理会话资源"""
    manager.disconnect(session_id)

    if session_id in interrupt_handlers:
        del interrupt_handlers[session_id]

    if session_id in dialogue_managers:
        del dialogue_managers[session_id]

    if session_id in session_settings:
        del session_settings[session_id]

    if session_id in session_knowledge_graphs:
        del session_knowledge_graphs[session_id]

    if session_id in session_multi_kgs:
        del session_multi_kgs[session_id]

    logger.info(f"[Session {session_id}] Resources cleaned up")


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)