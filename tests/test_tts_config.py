"""
TTS 配置测试
"""
import pytest
from src.models.tts_config import TTSConfig, VoiceConfig


def test_tts_config_creation():
    """测试 TTS 配置创建"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural",
            rate=1.0,
            pitch=0
        )
    )

    assert config.voice.language == "zh-CN"
    assert config.voice.name == "XiaoxiaoNeural"
    assert config.voice.rate == 1.0
    assert config.voice.pitch == 0


def test_tts_config_to_edge_tts_params():
    """测试转换为 Edge TTS 参数"""
    config = TTSConfig(
        voice=VoiceConfig(
            language="zh-CN",
            name="XiaoxiaoNeural",
            rate=1.2,
            pitch=-5
        )
    )

    params = config.to_edge_tts_params()

    assert params["voice"] == "zh-CN-XiaoxiaoNeural"
    assert params["rate"] == "+20%"
    assert params["pitch"] == "-5Hz"


def test_voice_config_default_values():
    """测试默认值"""
    voice = VoiceConfig()

    assert voice.language == "zh-CN"
    assert voice.name == "XiaoxiaoNeural"
    assert voice.rate == 1.0
    assert voice.pitch == 0


def test_voice_config_rate_bounds():
    """测试语速边界"""
    # 测试最小值
    voice_min = VoiceConfig(rate=0.5)
    assert voice_min.rate == 0.5

    # 测试最大值
    voice_max = VoiceConfig(rate=2.0)
    assert voice_max.rate == 2.0


def test_tts_config_copy():
    """测试配置复制"""
    config1 = TTSConfig(
        voice=VoiceConfig(rate=1.5, pitch=10)
    )

    config2 = config1.copy()
    config2.voice.rate = 1.0

    # 原配置不应被修改
    assert config1.voice.rate == 1.5
    assert config2.voice.rate == 1.0
