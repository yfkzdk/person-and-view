"""
导演指令解析器测试
"""
import pytest
from src.tts.director_parser import DirectorParser, DirectorCommand


def test_parse_volume_command():
    """解析音量指令"""
    parser = DirectorParser()

    text = "你好[压低音量]这是一段话"
    clean_text, commands = parser.parse(text)

    assert clean_text == "你好这是一段话"
    assert len(commands) == 1
    assert commands[0].command == "volume_down"
    assert commands[0].value == 0.7


def test_parse_speed_command():
    """解析语速指令"""
    parser = DirectorParser()

    text = "[加速]快说[减速]慢说"
    clean_text, commands = parser.parse(text)

    assert clean_text == "快说慢说"
    assert len(commands) == 2
    assert commands[0].command == "speed_up"
    assert commands[0].value == 1.3
    assert commands[1].command == "speed_down"
    assert commands[1].value == 0.7


def test_parse_emotion_command():
    """解析情绪指令"""
    parser = DirectorParser()

    text = "[情绪:开心]我很高兴"
    clean_text, commands = parser.parse(text)

    assert clean_text == "我很高兴"
    assert len(commands) == 1
    assert commands[0].command == "emotion"
    assert commands[0].value == "开心"


def test_parse_pause_command():
    """解析停顿指令"""
    parser = DirectorParser()

    text = "等等[停顿2秒]继续"
    clean_text, commands = parser.parse(text)

    assert clean_text == "等等继续"
    assert len(commands) == 1
    assert commands[0].command == "pause"
    assert commands[0].value == 2.0


def test_parse_multiple_commands():
    """解析多个指令"""
    parser = DirectorParser()

    text = "[压低音量][加速]快速低声说"
    clean_text, commands = parser.parse(text)

    assert clean_text == "快速低声说"
    assert len(commands) == 2


def test_apply_commands_to_config():
    """测试应用指令到配置"""
    parser = DirectorParser()
    from src.models.tts_config import TTSConfig, VoiceConfig

    base_config = TTSConfig(
        voice=VoiceConfig(rate=1.0)
    )

    commands = [
        DirectorCommand(command="speed_up", value=1.3),
        DirectorCommand(command="speed_down", value=0.7)
    ]

    modified_config = parser.apply_commands_to_config(commands, base_config)

    # 最终语速应该是 1.0 * 1.3 * 0.7 = 0.91
    assert abs(modified_config.voice.rate - 0.91) < 0.01


def test_get_voice_for_emotion():
    """测试情绪音色映射"""
    parser = DirectorParser()

    # 测试已知情绪
    assert parser._get_voice_for_emotion('开心') == 'XiaoxiaoNeural'
    assert parser._get_voice_for_emotion('悲伤') == 'YunxiNeural'

    # 测试未知情绪（返回默认）
    assert parser._get_voice_for_emotion('未知') == 'XiaoxiaoNeural'