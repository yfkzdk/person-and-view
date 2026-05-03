"""
导演指令解析器
"""
import re
from typing import List, Tuple
from src.models.tts_config import DirectorCommand, TTSConfig


class DirectorParser:
    """导演指令解析器"""

    # 指令模式定义
    DIRECTIVE_PATTERNS = {
        r'\[压低音量\]': ('volume_down', 0.7),
        r'\[提高音量\]': ('volume_up', 1.3),
        r'\[加速\]': ('speed_up', 1.3),
        r'\[减速\]': ('speed_down', 0.7),
        r'\[呼吸音\]': ('breath', 0.5),
        r'\[停顿(\d+(?:\.\d+)?)秒\]': ('pause', None),
        r'\[情绪:(\w+)\]': ('emotion', None),
    }

    def __init__(self):
        """初始化解析器"""
        self.compiled_patterns = []
        for pattern, (cmd_type, default_value) in self.DIRECTIVE_PATTERNS.items():
            self.compiled_patterns.append(
                (re.compile(pattern), cmd_type, default_value)
            )

    def parse(self, text: str) -> Tuple[str, List[DirectorCommand]]:
        """
        解析文本中的导演指令

        Args:
            text: 包含指令的文本

        Returns:
            (清理后的文本, 指令列表)
        """
        commands = []
        cleaned_text = text

        for compiled_pattern, cmd_type, default_value in self.compiled_patterns:
            matches = list(compiled_pattern.finditer(text))

            for match in matches:
                # 提取参数值
                if cmd_type == 'pause':
                    value = float(match.group(1)) if match.group(1) else default_value
                elif cmd_type == 'emotion':
                    value = match.group(1)
                else:
                    value = default_value

                # 创建指令对象
                command = DirectorCommand(
                    command=cmd_type,
                    value=value,
                    position=match.start()
                )
                commands.append(command)

                # 从文本中移除指令标记
                cleaned_text = cleaned_text.replace(match.group(0), '')

        # 按位置排序
        commands.sort(key=lambda c: c.position)

        return cleaned_text.strip(), commands

    def apply_commands_to_config(
        self,
        commands: List[DirectorCommand],
        base_config: TTSConfig
    ) -> TTSConfig:
        """
        将指令应用到 TTS 配置

        Args:
            commands: 指令列表
            base_config: 基础 TTS 配置

        Returns:
            修改后的配置
        """
        config = base_config.copy()

        for cmd in commands:
            if cmd.command == 'speed_up':
                config.voice.rate *= cmd.value
            elif cmd.command == 'speed_down':
                config.voice.rate *= cmd.value
            elif cmd.command == 'emotion':
                # 根据情绪调整音色
                config.voice.name = self._get_voice_for_emotion(cmd.value)

        # 限制范围
        config.voice.rate = max(0.5, min(2.0, config.voice.rate))

        return config

    def _get_voice_for_emotion(self, emotion: str) -> str:
        """
        根据情绪获取音色名称

        Args:
            emotion: 情绪标签

        Returns:
            音色名称
        """
        emotion_voice_map = {
            '开心': 'XiaoxiaoNeural',
            '悲伤': 'YunxiNeural',
            '愤怒': 'YunjianNeural',
            '平静': 'XiaoyiNeural',
        }

        return emotion_voice_map.get(emotion, 'XiaoxiaoNeural')