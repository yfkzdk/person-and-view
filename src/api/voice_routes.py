"""
声线克隆API - 提供完整的声线管理 RESTful 接口

功能:
- 列出/获取/创建/删除声音配置
- 从参考音频克隆声音
- 分析音频特征
- 声音与角色绑定管理
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
import tempfile
import logging

from src.tts.voice_profile_manager import VoiceProfileManager, VoiceProfile, PRESET_VOICES, get_voice_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

voice_manager = get_voice_manager()


# ====== 数据模型 ======

class VoiceProfileResponse(BaseModel):
    name: str
    description: str
    voice: str
    rate: float
    pitch: int
    style: str
    role: str
    cloned_from: str = ""
    clone_quality: float = 0.0
    character_binding: Optional[str] = None

    class Config:
        from_attributes = True


class VoiceCloneRequest(BaseModel):
    name: str
    description: str = ""
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: float = 1.0
    pitch: int = 0
    style: str = "neutral"
    role: str = "Girl"


class CharacterVoiceBinding(BaseModel):
    character_name: str
    voice_name: str


class AudioFeatureResponse(BaseModel):
    filename: str
    duration: float
    sample_rate: int = 0
    features: Dict[str, Any] = {}
    recommended_voice: str = ""
    recommended_rate: float = 1.0
    recommended_pitch: int = 0
    recommended_style: str = "neutral"


# ====== API 端点 ======

@router.get("/profiles", response_model=List[VoiceProfileResponse])
async def list_voice_profiles():
    """列出所有声音配置（预设 + 自定义）"""
    profiles = []
    for name in voice_manager.list_all():
        p = voice_manager.get_profile(name)
        if p:
            character_binding = None
            # 检查是否有角色绑定了此声音
            for cname, vname in _get_character_voice_bindings().items():
                if vname == name:
                    character_binding = cname
                    break
            profiles.append(VoiceProfileResponse(
                name=p.get("name", ""),
                description=p.get("description", ""),
                voice=p.get("voice", ""),
                rate=p.get("rate", 1.0),
                pitch=p.get("pitch", 0),
                style=p.get("style", "neutral"),
                role=p.get("role", "Girl"),
                cloned_from=p.get("cloned_from", ""),
                clone_quality=p.get("clone_quality", 0.0),
                character_binding=character_binding
            ))
    return profiles


@router.get("/profiles/{name}", response_model=VoiceProfileResponse)
async def get_voice_profile(name: str):
    """获取单个声音配置"""
    p = voice_manager.get_profile(name)
    if not p:
        raise HTTPException(status_code=404, detail=f"Voice profile '{name}' not found")
    return VoiceProfileResponse(
        name=p.get("name", ""),
        description=p.get("description", ""),
        voice=p.get("voice", ""),
        rate=p.get("rate", 1.0),
        pitch=p.get("pitch", 0),
        style=p.get("style", "neutral"),
        role=p.get("role", "Girl"),
        cloned_from=p.get("cloned_from", ""),
        clone_quality=p.get("clone_quality", 0.0)
    )


@router.post("/profiles", response_model=VoiceProfileResponse)
async def create_voice_profile(request: VoiceCloneRequest):
    """手动创建声音配置"""
    profile = VoiceProfile(
        name=request.name,
        description=request.description,
        voice=request.voice,
        rate=request.rate,
        pitch=request.pitch,
        style=request.style,
        role=request.role
    )
    voice_manager.save_custom_profile(profile)
    return VoiceProfileResponse(
        name=profile.name,
        description=profile.description,
        voice=profile.voice,
        rate=profile.rate,
        pitch=profile.pitch,
        style=profile.style,
        role=profile.role
    )


@router.put("/profiles/{name}", response_model=VoiceProfileResponse)
async def update_voice_profile(name: str, request: VoiceCloneRequest):
    """更新声音配置"""
    existing = voice_manager.get_profile(name)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Voice profile '{name}' not found")

    profile = VoiceProfile(
        name=request.name or name,
        description=request.description,
        voice=request.voice,
        rate=request.rate,
        pitch=request.pitch,
        style=request.style,
        role=request.role
    )
    voice_manager.save_custom_profile(profile)
    return VoiceProfileResponse(
        name=profile.name,
        description=profile.description,
        voice=profile.voice,
        rate=profile.rate,
        pitch=profile.pitch,
        style=profile.style,
        role=profile.role
    )


@router.delete("/profiles/{name}")
async def delete_voice_profile(name: str):
    """删除自定义声音配置（预设不可删除）"""
    if name in PRESET_VOICES:
        raise HTTPException(status_code=400, detail="Cannot delete preset voice profiles")
    success = voice_manager.delete_custom_profile(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Voice profile '{name}' not found")
    return {"message": f"Voice profile '{name}' deleted"}


@router.post("/clone", response_model=VoiceProfileResponse)
async def clone_voice_from_audio(
    name: str = Form(...),
    description: str = Form(""),
    audio_file: UploadFile = File(...)
):
    """
    从参考音频克隆声音

    上传一段音频，系统分析其特征并创建匹配的声音配置。
    支持 wav/mp3/ogg 格式。
    """
    # 验证文件类型
    allowed_extensions = ('.wav', '.mp3', '.ogg', '.m4a', '.flac')
    if not audio_file.filename or not any(audio_file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(allowed_extensions)}"
        )

    # 保存上传文件
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "audio_references")
    os.makedirs(upload_dir, exist_ok=True)

    safe_filename = f"{name}_{audio_file.filename}"
    filepath = os.path.join(upload_dir, safe_filename)

    try:
        content = await audio_file.read()
        with open(filepath, 'wb') as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio file: {e}")

    # 克隆
    try:
        profile = voice_manager.clone_from_reference(
            name=name,
            reference_audio=filepath,
            description=description or f"从 {audio_file.filename} 克隆的声音",
            auto_tune=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {e}")

    return VoiceProfileResponse(
        name=profile.name,
        description=profile.description,
        voice=profile.voice,
        rate=profile.rate,
        pitch=profile.pitch,
        style=profile.style,
        role=profile.role,
        cloned_from=profile.cloned_from,
        clone_quality=profile.clone_quality
    )


@router.post("/analyze", response_model=AudioFeatureResponse)
async def analyze_audio_features(audio_file: UploadFile = File(...)):
    """分析音频特征（不创建声音配置）"""
    allowed_extensions = ('.wav', '.mp3', '.ogg', '.m4a', '.flac')
    if not audio_file.filename or not any(audio_file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(audio_file.filename)[1], delete=False) as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 分析
        manager = voice_manager
        tuned = manager._analyze_and_tune(tmp_path)
        features = tuned.get("features", {})

        return AudioFeatureResponse(
            filename=audio_file.filename,
            duration=features.get("duration", 0),
            features=features,
            recommended_voice=tuned.get("voice", "zh-CN-XiaoxiaoNeural"),
            recommended_rate=tuned.get("rate", 1.0),
            recommended_pitch=tuned.get("pitch", 0),
            recommended_style=tuned.get("style", "neutral")
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ====== 角色-声音绑定 ======

# 绑定存储文件
BINDINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice_profiles", "_character_voice_bindings.json")


def _get_character_voice_bindings() -> Dict[str, str]:
    """获取角色-声音绑定"""
    if os.path.exists(BINDINGS_FILE):
        try:
            with open(BINDINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # 默认绑定
    return {
        "童锦程": "tong_jincheng",
        "小云": "therapist",
        "小明": "friend",
        "分析师": "mentor",
    }


def _save_character_voice_bindings(bindings: Dict[str, str]):
    """保存角色-声音绑定"""
    os.makedirs(os.path.dirname(BINDINGS_FILE), exist_ok=True)
    with open(BINDINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bindings, f, ensure_ascii=False, indent=2)


@router.get("/character-voice-bindings")
async def list_character_voice_bindings():
    """列出所有角色-声音绑定"""
    return _get_character_voice_bindings()


@router.post("/bind-character-voice")
async def bind_character_voice(binding: CharacterVoiceBinding):
    """绑定角色与声音"""
    # 验证声音存在
    if not voice_manager.get_profile(binding.voice_name):
        raise HTTPException(status_code=404, detail=f"Voice profile '{binding.voice_name}' not found")

    bindings = _get_character_voice_bindings()
    bindings[binding.character_name] = binding.voice_name
    _save_character_voice_bindings(bindings)

    return {
        "message": f"Character '{binding.character_name}' bound to voice '{binding.voice_name}'",
        "bindings": bindings
    }


@router.delete("/unbind-character-voice/{character_name}")
async def unbind_character_voice(character_name: str):
    """解绑角色声音"""
    bindings = _get_character_voice_bindings()
    if character_name in bindings:
        del bindings[character_name]
        _save_character_voice_bindings(bindings)
        return {"message": f"Unbound '{character_name}'", "bindings": bindings}
    return {"message": f"'{character_name}' has no binding", "bindings": bindings}


# ====== 测试端点 ======

@router.post("/test/{voice_name}")
async def test_voice(voice_name: str, text: str = "你好，这是声音测试。让我用不一样的方式跟你说话。"):
    """测试声音——返回合成的音频"""
    from fastapi.responses import Response
    from src.tts.tts_streamer import _edge_tts_synthesize
    import io

    profile = voice_manager.get_profile(voice_name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Voice profile '{voice_name}' not found")

    audio_chunks = []
    async for chunk in _edge_tts_synthesize(
        text,
        voice=profile.get("voice"),
        rate=profile.get("rate"),
        pitch=profile.get("pitch"),
        style=profile.get("style")
    ):
        audio_chunks.append(chunk)

    audio_data = b"".join(audio_chunks)
    if not audio_data:
        raise HTTPException(status_code=500, detail="TTS generated no audio")

    # Determine content type based on profile
    content_type = "audio/wav" if profile.get("voice", "").endswith("wav") else "audio/mpeg"

    return Response(content=audio_data, media_type=content_type)


def setup_voice_routes(app):
    """将声音路由集成到 FastAPI 应用"""
    app.include_router(router)
