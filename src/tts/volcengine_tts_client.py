"""
Volcengine (火山引擎/豆包) WebSocket V3 TTS client.

Uses the bidirectional WebSocket binary frame protocol (docs/6561/1329505).
No local inference — all computation happens on Volcengine servers.
"""
import asyncio
import json
import logging
import struct
import uuid
import os
from typing import AsyncIterator, Optional

import websockets

logger = logging.getLogger(__name__)

# ── Protocol Constants ──────────────────────────────────────────
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message types (high nibble of byte 2)
FULL_CLIENT_REQUEST = 0b0001
FULL_SERVER_RESPONSE = 0b1001
AUDIO_ONLY_RESPONSE = 0b1011

# Message flags (low nibble of byte 2)
MSG_FLAG_WITH_EVENT = 0b0100

# Serialization types (high nibble of byte 3)
SERIALIZATION_JSON = 0b0001
SERIALIZATION_NONE = 0b0000

# Compression (low nibble of byte 3)
COMPRESSION_NONE = 0b0000

# Events
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
EVENT_CONNECTION_STARTED = 50
EVENT_CONNECTION_FAILED = 51
EVENT_CONNECTION_FINISHED = 52
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_SESSION_STARTED = 150
EVENT_SESSION_FINISHED = 152
EVENT_SESSION_FAILED = 153
EVENT_TASK_REQUEST = 200
EVENT_TTS_SENTENCE_START = 350
EVENT_TTS_SENTENCE_END = 351
EVENT_TTS_RESPONSE = 352

# WebSocket endpoint
WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
WS_RESOURCE_ID = "seed-tts-2.0"

# Voice speakers for seed-tts-2.0 (V3 big model)
# Currently authorized speakers on the account.
SPEAKERS = {
    "zh_female_xueayi": "zh_female_xueayi_saturn_bigtts",              # 儿童绘本 — narrative, calm
    "zh_female_keai": "saturn_zh_female_keainvsheng_tob",             # 可爱女生 — lively, casual
    "zh_male_liufei": "zh_male_liufei_uranus_bigtts",                 # 刘飞 — male
    "zh_male_jieshuo": "zh_male_jieshuoxiaoming_uranus_bigtts",       # 解说小明 — commentary
    "zh_male_linjia": "zh_male_linjiananhai_uranus_bigtts",           # 邻家男孩 — boy next door
}

CHARACTER_VOICE_VOLC = {
    "tong_jincheng": {"speaker": "zh_male_linjiananhai_uranus_bigtts", "speed": 1.02, "volume": 1.0, "desc": "邻家男孩 — 适合童锦程"},
    "therapist": {"speaker": "zh_female_xueayi_saturn_bigtts", "speed": 0.9, "volume": 1.0, "desc": "儿童绘本女声 — 温柔叙事的心理咨询"},
    "friend": {"speaker": "saturn_zh_female_keainvsheng_tob", "speed": 1.0, "volume": 1.0, "desc": "可爱女声 — 适合日常对话"},
    "mentor": {"speaker": "zh_male_jieshuoxiaoming_uranus_bigtts", "speed": 0.9, "volume": 1.0, "desc": "解说小明 — 沉稳专业的导师"},
    "storyteller": {"speaker": "zh_female_xueayi_saturn_bigtts", "speed": 0.92, "volume": 1.0, "desc": "儿童绘本女声 — 适合叙事"},
    "companion": {"speaker": "zh_male_liufei_uranus_bigtts", "speed": 1.0, "volume": 1.0, "desc": "刘飞男声 — 陪伴感"},
}


def get_volc_voice(profile_name: str) -> dict:
    return CHARACTER_VOICE_VOLC.get(profile_name, {"speaker": "zh_male_linjiananhai_uranus_bigtts", "speed": 1.0, "volume": 1.0})


# ── Frame Helpers ───────────────────────────────────────────────

def _build_header(msg_type: int, msg_flags: int = MSG_FLAG_WITH_EVENT,
                  serial: int = SERIALIZATION_JSON, compression: int = COMPRESSION_NONE) -> bytes:
    b1 = (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE
    b2 = (msg_type << 4) | msg_flags
    b3 = (serial << 4) | compression
    b4 = 0
    return bytes([b1, b2, b3, b4])


def _build_optional(event: int, session_id: str = None) -> bytes:
    opt = bytearray()
    opt.extend(struct.pack(">i", event))
    if session_id is not None:
        sid_bytes = session_id.encode()
        opt.extend(struct.pack(">I", len(sid_bytes)))
        opt.extend(sid_bytes)
    return bytes(opt)


def _pack_frame(msg_type: int, optional: bytes, payload: bytes = b"") -> bytes:
    header = _build_header(msg_type)
    frame = bytearray(header)
    frame.extend(optional)
    frame.extend(struct.pack(">I", len(payload)))
    frame.extend(payload)
    return bytes(frame)


def _parse_frame(data: bytes) -> dict:
    """Parse a received binary frame. Returns {msg_type, event, payload}."""
    if len(data) < 4:
        return {"msg_type": None, "event": None, "payload": data}
    msg_type = (data[1] >> 4) & 0x0F
    msg_flags = data[1] & 0x0F
    result = {"msg_type": msg_type, "event": None, "payload": None}

    if msg_type == AUDIO_ONLY_RESPONSE:
        raw_payload = data[4:]
        # Check if this audio frame carries an embedded event
        if msg_flags & MSG_FLAG_WITH_EVENT and len(raw_payload) >= 8:
            result["event"] = struct.unpack(">i", raw_payload[0:4])[0]
            event_payload_len = struct.unpack(">I", raw_payload[4:8])[0]
            # After event header + payload, there's a 4-byte length prefix before actual audio
            audio_start = 8 + event_payload_len
            if len(raw_payload) >= audio_start + 4:
                # Skip the 4-byte audio length prefix
                result["payload"] = raw_payload[audio_start + 4:]
            else:
                result["payload"] = b""
        else:
            result["payload"] = raw_payload
        return result

    # Handle FULL_SERVER_RESPONSE (9) and ERROR_RESPONSE (15)
    if msg_type in (FULL_SERVER_RESPONSE, 0x0F) and len(data) >= 8:
        result["event"] = struct.unpack(">i", data[4:8])[0]
        if len(data) > 8:
            payload_len = struct.unpack(">I", data[8:12])[0]
            if len(data) >= 12 + payload_len:
                payload_bytes = data[12:12 + payload_len]
                try:
                    result["payload"] = json.loads(payload_bytes.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    result["payload"] = payload_bytes

    return result


# ── Synthesis ───────────────────────────────────────────────────

class StreamingVolcengineSynthesizer:
    """Sentence-level streaming TTS via a single V3 bidirectional WebSocket session.

    Usage:
        async with StreamingVolcengineSynthesizer(...) as synth:
            # Feed sentences as they become available from LLM
            await synth.feed_sentence("你好，我是AI助手。")
            await synth.feed_sentence("今天天气真不错。")
            # Finish and collect all audio
            async for audio_chunk in synth.flush():
                yield audio_chunk
    """

    def __init__(
        self,
        appid: str,
        token: str,
        speaker: str,
        speed: float = 1.0,
        volume: float = 1.0,
        audio_format: str = "mp3",
    ):
        self._appid = appid
        self._token = token
        self._speaker = speaker
        self._speed = speed
        self._volume = volume
        self._format = audio_format
        self._session_id = uuid.uuid4().hex
        self._ws = None
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._recv_task: asyncio.Task = None
        self._started = False
        self._input_done = False
        self._recv_done = False
        self._error = None

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(self, *args):
        await self._cleanup()

    async def _connect(self):
        """Establish WebSocket connection and start session."""
        headers = {
            "X-Api-App-Id": self._appid,
            "X-Api-Access-Key": self._token,
            "X-Api-Resource-Id": WS_RESOURCE_ID,
        }
        speech_rate = max(-50, min(100, int(round((self._speed - 1.0) * 100))))

        self._ws = await websockets.connect(WS_URL, extra_headers=headers, max_size=2**24)

        # START_CONNECTION
        opt = _build_optional(EVENT_START_CONNECTION)
        payload = json.dumps({"appid": self._appid, "token": self._token}).encode()
        await self._ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, payload))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
        parsed = _parse_frame(raw)
        if parsed["event"] != EVENT_CONNECTION_STARTED:
            raise RuntimeError(f"CONN failed: event={parsed['event']}")

        # START_SESSION
        opt = _build_optional(EVENT_START_SESSION, self._session_id)
        session_payload = json.dumps({
            "user": {"uid": f"user_{self._session_id[:8]}"},
            "event": EVENT_START_SESSION,
            "namespace": "BidirectionalTTS",
            "req_params": {
                "speaker": self._speaker,
                "audio_params": {
                    "format": self._format,
                    "sample_rate": 24000,
                    "speech_rate": speech_rate,
                    "volume": self._volume,
                },
            },
        }).encode()
        await self._ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, session_payload))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
        parsed = _parse_frame(raw)
        if parsed["event"] != EVENT_SESSION_STARTED:
            raise RuntimeError(f"SESSION failed: event={parsed['event']}")

        self._started = True
        # Start background receiver
        self._recv_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        """Background task: receive frames and push audio to queue."""
        try:
            while not self._recv_done:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=30)
                parsed = _parse_frame(raw)

                if parsed["msg_type"] == AUDIO_ONLY_RESPONSE:
                    if parsed["payload"]:
                        await self._audio_queue.put(("audio", parsed["payload"]))

                elif parsed["msg_type"] == 0x0F:
                    pl = parsed.get("payload", {})
                    err_msg = pl.get("error", str(pl)) if isinstance(pl, dict) else str(pl)
                    logger.error(f"Streaming TTS server error: {err_msg}")
                    await self._audio_queue.put(("error", err_msg))
                    break

                elif parsed["event"] == EVENT_SESSION_FINISHED:
                    await self._audio_queue.put(("session_finished", None))
                    break
                elif parsed["event"] == EVENT_SESSION_FAILED:
                    logger.error(f"Session failed: {parsed.get('payload')}")
                    await self._audio_queue.put(("error", "session_failed"))
                    break

        except asyncio.TimeoutError:
            logger.error("Streaming TTS receive timeout")
            await self._audio_queue.put(("error", "timeout"))
        except websockets.exceptions.ConnectionClosed as e:
            if not self._recv_done:
                logger.error(f"WebSocket closed unexpectedly: {e}")
                await self._audio_queue.put(("error", str(e)))
        except Exception as e:
            logger.error(f"Streaming TTS receive error: {e}")
            await self._audio_queue.put(("error", str(e)))

    async def feed_sentence(self, text: str):
        """Send a sentence to TTS for synthesis. Can call multiple times."""
        if not self._started:
            raise RuntimeError("Synthesizer not started")
        if self._input_done:
            raise RuntimeError("Synthesizer already finished")
        if not text.strip():
            return

        opt = _build_optional(EVENT_TASK_REQUEST, self._session_id)
        task_payload = json.dumps({
            "user": {"uid": f"user_{self._session_id[:8]}"},
            "event": EVENT_TASK_REQUEST,
            "namespace": "BidirectionalTTS",
            "req_params": {
                "text": text.strip(),
                "speaker": self._speaker,
                "audio_params": {
                    "format": self._format,
                    "sample_rate": 24000,
                    "speech_rate": max(-50, min(100, int(round((self._speed - 1.0) * 100)))),
                    "volume": self._volume,
                },
            },
        }).encode()
        await self._ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, task_payload))

    async def finish(self):
        """Signal end of text input. Audio may still arrive after this."""
        if self._input_done:
            return
        self._input_done = True
        opt = _build_optional(EVENT_FINISH_SESSION, self._session_id)
        await self._ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, json.dumps({}).encode()))

    async def flush(self) -> AsyncIterator[bytes]:
        """Yield audio chunks as they arrive, until session completes."""
        if not self._started:
            return
        while True:
            msg_type, data = await self._audio_queue.get()
            if msg_type == "audio":
                yield data
            elif msg_type in ("error", "session_finished"):
                break

    async def _cleanup(self):
        """Send FINISH_CONNECTION and close WebSocket."""
        self._recv_done = True
        if self._ws:
            try:
                if self._started and not self._input_done:
                    await self.finish()
                opt = _build_optional(EVENT_FINISH_CONNECTION)
                await self._ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, json.dumps({}).encode()))
            except Exception:
                pass
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()


async def _ws_synthesize_stream(
    text: str,
    appid: str,
    token: str,
    speaker: str,
    speed: float = 1.0,
    volume: float = 1.0,
    audio_format: str = "mp3",
) -> AsyncIterator[bytes]:
    """Internal: connect via WebSocket V3, send text, yield audio chunks."""

    headers = {
        "X-Api-App-Id": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": WS_RESOURCE_ID,
    }

    session_id = uuid.uuid4().hex

    # Convert speed to Volcengine integer scale: 0=1.0x, 100=2.0x, -50=0.5x
    speech_rate = max(-50, min(100, int(round((speed - 1.0) * 100))))

    async with websockets.connect(WS_URL, extra_headers=headers, max_size=2**24) as ws:
        # 1. START_CONNECTION
        opt = _build_optional(EVENT_START_CONNECTION)
        payload = json.dumps({"appid": appid, "token": token}).encode()
        await ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, payload))

        # Wait for CONNECTION_STARTED
        raw = await ws.recv()
        parsed = _parse_frame(raw)
        if parsed["event"] != EVENT_CONNECTION_STARTED:
            err = parsed.get("payload", "unknown error")
            logger.error(f"Connection failed: event={parsed['event']}, payload={err}")
            return

        # 2. START_SESSION
        opt = _build_optional(EVENT_START_SESSION, session_id)
        session_payload = json.dumps({
            "user": {"uid": f"user_{session_id[:8]}"},
            "event": EVENT_START_SESSION,
            "namespace": "BidirectionalTTS",
            "req_params": {
                "speaker": speaker,
                "audio_params": {
                    "format": audio_format,
                    "sample_rate": 24000,
                    "speech_rate": speech_rate,
                    "volume": volume,
                },
            },
        }).encode()
        await ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, session_payload))

        # Wait for SESSION_STARTED
        raw = await ws.recv()
        parsed = _parse_frame(raw)
        if parsed["event"] != EVENT_SESSION_STARTED:
            logger.error(f"Session start failed: event={parsed['event']}")
            return

        # 3. TASK_REQUEST
        opt = _build_optional(EVENT_TASK_REQUEST, session_id)
        task_payload = json.dumps({
            "user": {"uid": f"user_{session_id[:8]}"},
            "event": EVENT_TASK_REQUEST,
            "namespace": "BidirectionalTTS",
            "req_params": {
                "text": text,
                "speaker": speaker,
                "audio_params": {
                    "format": audio_format,
                    "sample_rate": 24000,
                    "speech_rate": speech_rate,
                    "volume": volume,
                },
            },
        }).encode()
        await ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, task_payload))

        # 4. FINISH_SESSION (required — audio only arrives after this)
        opt = _build_optional(EVENT_FINISH_SESSION, session_id)
        await ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, json.dumps({}).encode()))

        # 5. Receive audio and control frames
        while True:
            raw = await ws.recv()
            parsed = _parse_frame(raw)

            if parsed["msg_type"] == AUDIO_ONLY_RESPONSE:
                if parsed["payload"]:
                    yield parsed["payload"]

            elif parsed["msg_type"] == 0x0F:
                # Error response from server
                pl = parsed.get("payload", {})
                err_msg = pl.get("error", str(pl)) if isinstance(pl, dict) else str(pl)
                logger.error(f"Server error: {err_msg}")
                break

            elif parsed["event"] in (EVENT_TTS_RESPONSE,):
                pl = parsed.get("payload", {})
                if isinstance(pl, dict) and "audio" in pl:
                    import base64
                    yield base64.b64decode(pl["audio"])
                elif isinstance(pl, bytes) and pl:
                    yield pl

            elif parsed["event"] == EVENT_SESSION_FINISHED:
                break
            elif parsed["event"] == EVENT_SESSION_FAILED:
                logger.error(f"Session failed: {parsed.get('payload')}")
                break

        # 6. FINISH_CONNECTION
        opt = _build_optional(EVENT_FINISH_CONNECTION)
        await ws.send(_pack_frame(FULL_CLIENT_REQUEST, opt, json.dumps({}).encode()))


async def volcengine_tts_synthesize(
    text: str,
    appid: str = None,
    token: str = None,
    voice_type: str = "zh_female_natural",
    speed: float = 1.0,
    volume: float = 1.0,
    emotion: str = None,
    fmt: str = "mp3",
) -> AsyncIterator[bytes]:
    """Stream-synthesize text via Volcengine WebSocket V3 TTS.

    Yields audio chunks as raw bytes (mp3 format).
    """
    appid = appid or os.environ.get("VOLCENGINE_APP_ID")
    token = token or os.environ.get("VOLCENGINE_ACCESS_TOKEN")

    if not appid or not token:
        logger.error("VOLCENGINE_APP_ID and VOLCENGINE_ACCESS_TOKEN must be set")
        return

    speaker = SPEAKERS.get(voice_type, voice_type)
    logger.info(f"Volcengine WS TTS: speaker={speaker}, speed={speed:.2f}, text_len={len(text)}")

    try:
        async for chunk in _ws_synthesize_stream(
            text=text,
            appid=appid,
            token=token,
            speaker=speaker,
            speed=speed,
            volume=volume,
            audio_format=fmt,
        ):
            yield chunk
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed: {e}")
    except Exception as e:
        logger.error(f"Volcengine WS TTS error: {e}")
