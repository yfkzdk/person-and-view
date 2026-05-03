"""
集中配置管理
"""
import os
from typing import Optional


class Settings:
    """全局配置"""

    # 服务器配置
    HOST: str = os.environ.get("SERVER_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("SERVER_PORT", "8000"))

    # Redis 配置
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379")
    REDIS_ENABLED: bool = os.environ.get("REDIS_ENABLED", "false").lower() == "true"

    # VAD 配置
    VAD_SAMPLE_RATE: int = int(os.environ.get("VAD_SAMPLE_RATE", "16000"))
    VAD_THRESHOLD: float = float(os.environ.get("VAD_THRESHOLD", "0.5"))

    # TTS 配置
    TTS_PROVIDER: str = os.environ.get("TTS_PROVIDER", "edge_tts")  # edge_tts 或 cosyvoice
    TTS_LANGUAGE: str = os.environ.get("TTS_LANGUAGE", "zh-CN")
    TTS_VOICE: str = os.environ.get("TTS_VOICE", "XiaoxiaoNeural")
    TTS_RATE: float = float(os.environ.get("TTS_RATE", "1.0"))
    TTS_PITCH: int = int(os.environ.get("TTS_PITCH", "0"))

    # CosyVoice 配置
    COSYVOICE_MODEL_DIR: str = os.environ.get("COSYVOICE_MODEL_DIR", "")
    COSYVOICE_REF_AUDIO: str = os.environ.get("COSYVOICE_REF_AUDIO", "")
    COSYVOICE_REF_TEXT: str = os.environ.get("COSYVOICE_REF_TEXT", "You are a helpful assistant.<|endofprompt|>大家好。")

    # Voice profiles - comma-separated list of profile names
    COSYVOICE_VOICES: str = os.environ.get("COSYVOICE_VOICES", "tong_jincheng")
    # Default voice profile
    COSYVOICE_DEFAULT_VOICE: str = os.environ.get("COSYVOICE_DEFAULT_VOICE", "tong_jincheng")

    # LLM 配置 - 支持多个提供商
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "deepseek")  # anthropic 或 deepseek

    # Anthropic 配置
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

    # DeepSeek 配置
    DEEPSEEK_API_KEY: Optional[str] = os.environ.get("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    # 通用 LLM 配置
    LLM_MAX_TOKENS: int = int(os.environ.get("LLM_MAX_TOKENS", "2000"))
    LLM_TEMPERATURE: float = float(os.environ.get("LLM_TEMPERATURE", "0.7"))

    # 会话配置
    MAX_HISTORY: int = int(os.environ.get("MAX_HISTORY", "10"))
    LOCAL_CACHE_SIZE: int = int(os.environ.get("LOCAL_CACHE_SIZE", "100"))

    # 音频配置
    AUDIO_CHUNK_SIZE: int = int(os.environ.get("AUDIO_CHUNK_SIZE", "512"))

    # 记忆系统配置
    MEMORY_MAX_FILE_SIZE: int = int(os.environ.get("MEMORY_MAX_FILE_SIZE", "10485760"))  # 10MB
    MEMORY_AUTO_SAVE: bool = os.environ.get("MEMORY_AUTO_SAVE", "true").lower() == "true"

    # 数据库配置
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///data/voices.db")


settings = Settings()