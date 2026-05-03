"""
声线管理系统 - 为每个角色绑定自定义声音配置

支持:
- Edge TTS 精确调参 (voice name, rate, pitch, style)
- 角色声音绑定
- 声音预设库
- 从参考音频分析声音特征
"""
import json
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# 声音配置存储目录
VOICE_PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice_profiles")
os.makedirs(VOICE_PROFILES_DIR, exist_ok=True)


@dataclass
class VoiceProfile:
    """声音配置"""
    name: str                          # 配置名称
    description: str = ""              # 描述
    voice: str = "zh-CN-XiaoxiaoNeural"  # Edge TTS voice name
    rate: float = 1.0                  # 语速 (-50% ~ +200%)
    pitch: int = 0                     # 音调 (-50Hz ~ +50Hz)
    style: str = "neutral"             # 说话风格
    role: str = "Girl"                 # 角色 (Girl/Boy/Woman/Man/Senior)

    # 声线模仿参数
    cloned_from: str = ""              # 克隆源（录音文件名）
    reference_audio: str = ""          # 参考音频路径
    clone_quality: float = 0.0         # 克隆质量分 (0-1)

    # 扩展
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        # 过滤空值
        return {k: v for k, v in d.items() if v or k in ("name", "voice", "rate", "pitch")}

    @classmethod
    def from_dict(cls, data: Dict) -> "VoiceProfile":
        # 确保必需字段有默认值
        defaults = {
            "name": "", "description": "", "voice": "zh-CN-XiaoxiaoNeural",
            "rate": 1.0, "pitch": 0, "style": "neutral", "role": "Girl",
            "cloned_from": "", "reference_audio": "", "clone_quality": 0.0, "extra": {}
        }
        defaults.update(data)
        return cls(**{k: defaults[k] for k in defaults})


# ====== 预设声音库 ======

PRESET_VOICES: Dict[str, VoiceProfile] = {
    # --- 女声 ---
    "xiaoxiao": VoiceProfile(
        name="xiaoxiao",
        description="温柔活泼的年轻女声，适合朋友/伙伴角色",
        voice="zh-CN-XiaoxiaoNeural",
        rate=1.0, pitch=0, style="friendly", role="Girl"
    ),
    "xiaoyi": VoiceProfile(
        name="xiaoyi",
        description="明快俏皮的女声，适合活泼可爱的角色",
        voice="zh-CN-XiaoyiNeural",
        rate=1.05, pitch=5, style="cheerful", role="Girl"
    ),
    "yunjian": VoiceProfile(
        name="yunjian",
        description="清澈自然的年轻女声，适合叙事/朗读",
        voice="zh-CN-YunjianNeural",
        rate=0.95, pitch=0, style="narration-relaxed", role="Girl"
    ),
    "yunxia": VoiceProfile(
        name="yunxia",
        description="开朗甜美的女声，适合活泼角色",
        voice="zh-CN-YunxiaNeural",
        rate=1.0, pitch=5, style="lively", role="Girl"
    ),
    "xiaobei": VoiceProfile(
        name="xiaobei",
        description="东北话女声，接地气、幽默风格",
        voice="zh-CN-liaoning-XiaobeiNeural",
        rate=1.05, pitch=0, style="friendly", role="Girl"
    ),

    # --- 男声 ---
    "yunxi": VoiceProfile(
        name="yunxi",
        description="沉稳专业的男声，适合导师/专家角色",
        voice="zh-CN-YunxiNeural",
        rate=0.9, pitch=-5, style="professional", role="Man"
    ),
    "yunyang": VoiceProfile(
        name="yunyang",
        description="温暖亲切的男声，适合情感/陪伴角色",
        voice="zh-CN-YunyangNeural",
        rate=0.95, pitch=-2, style="warm", role="Man"
    ),
    "henan_man": VoiceProfile(
        name="henan_man",
        description="河南话男声，朴实、亲切",
        voice="zh-CN-henan-YundengNeural",
        rate=1.0, pitch=0, style="friendly", role="Man"
    ),

    # --- 角色专用声音 ---
    "tong_jincheng": VoiceProfile(
        name="tong_jincheng",
        description="童锦程风格——自信、直率、接地气的男声",
        voice="zh-CN-YunyangNeural",
        rate=1.05, pitch=0, style="friendly", role="Man",
        extra={
            "character": "童锦程",
            "speaking_traits": ["自信", "直率", "接地气", "偶尔自嘲"],
            "pace": "中等偏快",
            "energy": "high"
        }
    ),
    "therapist": VoiceProfile(
        name="therapist",
        description="温暖柔和的心理咨询师声音",
        voice="zh-CN-XiaoxiaoNeural",
        rate=0.85, pitch=-3, style="gentle", role="Woman",
        extra={
            "character": "小云",
            "speaking_traits": ["温暖", "耐心", "共情"],
            "pace": "缓慢稳重",
            "energy": "calm"
        }
    ),
    "storyteller": VoiceProfile(
        name="storyteller",
        description="叙事风格的温暖女声",
        voice="zh-CN-YunjianNeural",
        rate=0.9, pitch=0, style="narration-relaxed", role="Girl"
    ),
    "mentor": VoiceProfile(
        name="mentor",
        description="导师风格——沉稳、睿智",
        voice="zh-CN-YunxiNeural",
        rate=0.85, pitch=-5, style="serious", role="Man"
    ),
    "companion": VoiceProfile(
        name="companion",
        description="伙伴风格——轻松、亲切",
        voice="zh-CN-XiaoyiNeural",
        rate=1.0, pitch=5, style="friendly", role="Girl"
    ),
    "friend": VoiceProfile(
        name="friend",
        description="朋友风格——自然随意",
        voice="zh-CN-XiaoxiaoNeural",
        rate=1.0, pitch=0, style="warm", role="Girl"
    ),
}


class VoiceProfileManager:
    """声音配置管理器"""

    def __init__(self, profiles_dir: str = VOICE_PROFILES_DIR):
        self.profiles_dir = profiles_dir
        self._custom_profiles: Dict[str, VoiceProfile] = {}
        self._load_custom_profiles()

    def _load_custom_profiles(self):
        """加载自定义声音配置"""
        if not os.path.exists(self.profiles_dir):
            return
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(self.profiles_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    profile = VoiceProfile.from_dict(data)
                    self._custom_profiles[profile.name] = profile
                except Exception as e:
                    logger.warning(f"Failed to load voice profile {filename}: {e}")

    def get_profile(self, name: str) -> Optional[Dict]:
        """获取声音配置（预设 + 自定义）"""
        # 先查预设
        if name in PRESET_VOICES:
            return PRESET_VOICES[name].to_dict()
        # 再查自定义
        if name in self._custom_profiles:
            return self._custom_profiles[name].to_dict()
        # 模糊匹配
        all_profiles = self.list_all()
        for pname in all_profiles:
            if name.lower() in pname.lower():
                return self.get_profile(pname)
        return None

    def list_profiles(self) -> List[str]:
        """列出所有声音名称"""
        preset_names = list(PRESET_VOICES.keys())
        custom_names = list(self._custom_profiles.keys())
        return sorted(preset_names + custom_names)

    def list_all(self) -> List[str]:
        """列出所有声音（包括预设和自定义）"""
        return self.list_profiles()

    def get_profile_for_character(self, character_name: str) -> Dict:
        """根据角色名获取最佳匹配声音"""
        # 先检查预设中是否有角色专用声音
        for name, profile in PRESET_VOICES.items():
            if profile.extra.get('character') == character_name:
                return profile.to_dict()

        # 字符到声音的映射
        character_voice_map = {
            "童锦程": "tong_jincheng",
            "小云": "therapist",
            "小明": "friend",
            "分析师": "mentor",
        }

        voice_name = character_voice_map.get(character_name)
        if voice_name:
            return self.get_profile(voice_name) or self.get_profile("xiaoxiao")

        return self.get_profile("xiaoxiao")

    def save_custom_profile(self, profile: VoiceProfile) -> str:
        """保存自定义声音配置"""
        self._custom_profiles[profile.name] = profile
        filepath = os.path.join(self.profiles_dir, f"{profile.name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        return filepath

    def delete_custom_profile(self, name: str) -> bool:
        """删除自定义声音配置"""
        if name not in self._custom_profiles:
            return False
        del self._custom_profiles[name]
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        return True

    def clone_from_reference(
        self,
        name: str,
        reference_audio: str,
        description: str = "",
        auto_tune: bool = True
    ) -> VoiceProfile:
        """
        从参考音频克隆声音

        Args:
            name: 克隆声音的名称
            reference_audio: 参考音频路径
            description: 描述
            auto_tune: 是否自动调优 Edge TTS 参数以匹配参考音频
        """
        profile = VoiceProfile(
            name=name,
            description=description or f"从 {os.path.basename(reference_audio)} 克隆",
            cloned_from=os.path.basename(reference_audio),
            reference_audio=reference_audio,
            clone_quality=0.0
        )

        if auto_tune and os.path.exists(reference_audio):
            # 分析参考音频特征并自动调优
            tuned_params = self._analyze_and_tune(reference_audio)
            profile.voice = tuned_params.get("voice", profile.voice)
            profile.rate = tuned_params.get("rate", profile.rate)
            profile.pitch = tuned_params.get("pitch", profile.pitch)
            profile.style = tuned_params.get("style", profile.style)
            profile.role = tuned_params.get("role", profile.role)
            profile.clone_quality = tuned_params.get("quality", 0.5)
            profile.extra["audio_features"] = tuned_params.get("features", {})

        self.save_custom_profile(profile)
        return profile

    def _analyze_and_tune(self, audio_path: str) -> Dict:
        """
        分析参考音频并返回最佳 Edge TTS 参数

        使用 librosa 提取音频特征，映射到 Edge TTS 参数
        """
        features = {
            "duration": 0, "pitch_mean": 0, "pitch_std": 0,
            "rms_energy": 0, "spectral_centroid": 0, "zero_crossing_rate": 0
        }

        quality = 0.3  # 基础质量分

        try:
            import numpy as np
            import soundfile as sf

            audio, sr = sf.read(audio_path)
            duration = len(audio) / sr
            features["duration"] = round(duration, 2)

            # 如果是立体声，转单声道
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # RMS 能量
            rms = np.sqrt(np.mean(audio ** 2))
            features["rms_energy"] = round(float(rms), 4)

            # 过零率 (估计音高)
            zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2.0
            features["zero_crossing_rate"] = round(float(zcr), 4)

            # 频谱质心 (亮度)
            try:
                import numpy.fft as fft
                spec = np.abs(fft.rfft(audio[:min(len(audio), sr * 10)]))
                freqs = fft.rfftfreq(min(len(audio), sr * 10), 1.0 / sr)
                spectral_centroid = np.sum(freqs * spec) / np.sum(spec)
                features["spectral_centroid"] = round(float(spectral_centroid), 2)
            except Exception:
                pass

            quality = 0.5

        except ImportError:
            logger.warning("soundfile not available, using basic analysis")
            try:
                import wave
                with wave.open(audio_path, 'rb') as wf:
                    features["duration"] = wf.getnframes() / wf.getframerate()
                quality = 0.2
            except Exception:
                logger.warning(f"Cannot analyze {audio_path}")
                quality = 0.1

        # 根据特征映射到 Edge TTS 参数
        zcr_val = features.get("zero_crossing_rate", 0.05)
        energy = features.get("rms_energy", 0.1)

        # 音高判断: 过零率越高 → 音调越高
        if zcr_val > 0.08:
            voice = "zh-CN-XiaoxiaoNeural"  # 偏女声
            role = "Girl"
            pitch = min(20, int((zcr_val - 0.05) * 200))
        elif zcr_val > 0.05:
            voice = "zh-CN-YunjianNeural"
            role = "Girl"
            pitch = int((zcr_val - 0.05) * 100)
        else:
            voice = "zh-CN-YunxiNeural"  # 偏男声
            role = "Man"
            pitch = max(-20, int((zcr_val - 0.05) * 150))

        # 语速: 能量高 → 语速快
        if energy > 0.3:
            rate = 1.1
        elif energy < 0.1:
            rate = 0.85
        else:
            rate = 1.0

        # 风格
        style = "friendly"
        centroid = features.get("spectral_centroid", 1000)
        if centroid > 2000:
            style = "cheerful"
        elif centroid < 500:
            style = "serious"

        return {
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "style": style,
            "role": role,
            "quality": quality,
            "features": features
        }


# 全局单例
_voice_manager: Optional[VoiceProfileManager] = None


def get_voice_manager() -> VoiceProfileManager:
    """获取全局声音管理器"""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceProfileManager()
    return _voice_manager
