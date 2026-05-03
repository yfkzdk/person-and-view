"""
TTS 配置模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Union


class VoiceConfig(BaseModel):
    """音色配置"""
    language: str = "zh-CN"
    name: str = "XiaoxiaoNeural"
    rate: float = Field(1.0, ge=0.5, le=2.0, description="语速倍率")
    pitch: int = Field(0, ge=-50, le=50, description="音调偏移 (Hz)")

    def to_edge_tts_rate(self) -> str:
        """转换为 Edge TTS 语速格式"""
        percentage = round((self.rate - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        else:
            return f"{percentage}%"

    def to_edge_tts_pitch(self) -> str:
        """转换为 Edge TTS 音调格式"""
        if self.pitch >= 0:
            return f"+{self.pitch}Hz"
        else:
            return f"{self.pitch}Hz"


class TTSConfig(BaseModel):
    """TTS 配置"""
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    output_format: str = "audio-24khz-48kbitrate-mono-mp3"

    def to_edge_tts_params(self) -> dict:
        """转换为 Edge TTS 参数"""
        voice_name = f"{self.voice.language}-{self.voice.name}"

        return {
            "voice": voice_name,
            "rate": self.voice.to_edge_tts_rate(),
            "pitch": self.voice.to_edge_tts_pitch(),
        }

    def copy(self) -> 'TTSConfig':
        """创建副本"""
        return TTSConfig(
            voice=VoiceConfig(
                language=self.voice.language,
                name=self.voice.name,
                rate=self.voice.rate,
                pitch=self.voice.pitch
            ),
            output_format=self.output_format
        )


class DirectorCommand(BaseModel):
    """导演指令"""
    command: str
    value: Optional[Union[float, str]] = None
    position: int = 0  # 在文本中的位置
