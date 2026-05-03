"""
CosyVoice TTS 客户端 - 零样本语音克隆
通过子进程调用 CosyVoice venv 的 Python，避免 torch DLL 冲突
"""
import os
import asyncio
import tempfile
import logging

from src.config import settings

logger = logging.getLogger(__name__)

# CosyVoice paths
COSYVOICE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "external", "CosyVoice")
COSYVOICE_VENV_PYTHON = os.path.join(COSYVOICE_DIR, "venv", "Scripts", "python.exe")

# Voice profiles mapping
VOICE_PROFILES = {
    "tong_jincheng": {
        "ref_audio": "ref_audio/tong_jincheng_ref.wav",
        "ref_text": "You are a helpful assistant.<|endofprompt|>大家好。"
    }
}


def get_voice_profile(voice_name: str) -> dict:
    """Get voice profile config by name"""
    if voice_name in VOICE_PROFILES:
        profile = VOICE_PROFILES[voice_name]
        return {
            "ref_audio": os.path.join(COSYVOICE_DIR, profile["ref_audio"]),
            "ref_text": profile["ref_text"]
        }
    # If not a known profile, treat as a file path
    return {
        "ref_audio": os.path.join(COSYVOICE_DIR, "ref_audio", voice_name) if not os.path.isabs(voice_name) else voice_name,
        "ref_text": settings.COSYVOICE_REF_TEXT
    }

# Inference script template - runs inside CosyVoice venv
INFERENCE_SCRIPT = '''
import sys
import os
sys.path.insert(0, os.path.join(r"{cosyvoice_dir}", "third_party", "Matcha-TTS"))
sys.path.insert(0, r"{cosyvoice_dir}")

from cosyvoice.cli.cosyvoice import CosyVoice3
import soundfile as sf
import numpy as np

model_dir = r"{model_dir}"
ref_audio = r"{ref_audio}"
ref_text = r"{ref_text}"
tts_text = r"{tts_text}"
output_path = r"{output_path}"

model = CosyVoice3(model_dir=model_dir)

audio_chunks = []
for i, j in enumerate(model.inference_zero_shot(tts_text, ref_text, ref_audio, stream=False)):
    audio_chunks.append(j['tts_speech'])

if audio_chunks:
    import torch
    full_audio = torch.cat(audio_chunks, dim=1)
    audio_np = full_audio.squeeze(0).cpu().float().numpy()
    sf.write(output_path, audio_np, model.sample_rate, format='WAV')
    print(f"OK:{{len(audio_np)}}:{{model.sample_rate}}")
else:
    print("FAIL:no_audio")
'''


# Streaming inference script template - uses CosyVoice stream=True
STREAMING_INFERENCE_SCRIPT = '''
import sys
import os
sys.path.insert(0, os.path.join(r"{cosyvoice_dir}", "third_party", "Matcha-TTS"))
sys.path.insert(0, r"{cosyvoice_dir}")

from cosyvoice.cli.cosyvoice import CosyVoice3
import soundfile as sf
import numpy as np

model_dir = r"{model_dir}"
ref_audio = r"{ref_audio}"
ref_text = r"{ref_text}"
tts_text = r"{tts_text}"
output_dir = r"{output_dir}"

model = CosyVoice3(model_dir=model_dir)

chunk_idx = 0
for i, j in enumerate(model.inference_zero_shot(tts_text, ref_text, ref_audio, stream=True)):
    audio_np = j['tts_speech'].squeeze(0).cpu().float().numpy()
    chunk_path = os.path.join(output_dir, f"chunk_{{chunk_idx:04d}}.wav")
    sf.write(chunk_path, audio_np, model.sample_rate, format='WAV')
    chunk_idx += 1

print(f"CHUNKS:{{chunk_idx}}")
'''


class CosyVoiceTTSClient:
    """CosyVoice 零样本语音克隆 TTS 客户端（子进程模式）"""

    def __init__(self, model_dir: str = None, ref_audio: str = None,
                 ref_text: str = None, sample_rate: int = 24000,
                 voice_name: str = None):
        self.model_dir = model_dir or os.path.join(COSYVOICE_DIR,
            "pretrained_models", "Fun-CosyVoice3-0.5B")
        self.sample_rate = sample_rate
        self.voice_name = voice_name

        # If voice_name is provided, resolve via profile; otherwise use explicit paths
        if voice_name:
            profile = get_voice_profile(voice_name)
            self.ref_audio = ref_audio or profile["ref_audio"]
            self.ref_text = ref_text or profile["ref_text"]
        else:
            self.ref_audio = ref_audio
            self.ref_text = ref_text or "You are a helpful assistant.<|endofprompt|>大家好。"

    def switch_voice(self, voice_name: str):
        """Switch to a different voice profile, resetting state so next synthesis uses it"""
        profile = get_voice_profile(voice_name)
        self.voice_name = voice_name
        self.ref_audio = profile["ref_audio"]
        self.ref_text = profile["ref_text"]
        logger.info(f"Switched voice to '{voice_name}': ref_audio={self.ref_audio}")

    async def synthesize(self, text: str) -> bytes:
        """
        合成文本为音频（通过子进程调用 CosyVoice venv）

        Args:
            text: 要合成的文本

        Returns:
            WAV格式的音频数据 (bytes)
        """
        logger.info(f"CosyVoice synthesizing: {text[:50]}...")

        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_path = tmp.name

        try:
            script = INFERENCE_SCRIPT.format(
                cosyvoice_dir=COSYVOICE_DIR,
                model_dir=self.model_dir,
                ref_audio=self.ref_audio,
                ref_text=self.ref_text,
                tts_text=text,
                output_path=output_path,
            )

            # Write script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as script_file:
                script_file.write(script)
                script_path = script_file.name

            # Run in CosyVoice venv's Python (with timeout)
            proc = await asyncio.create_subprocess_exec(
                COSYVOICE_VENV_PYTHON, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.error("CosyVoice process timed out after 120s")
                return b''

            # Clean up script file
            try:
                os.unlink(script_path)
            except OSError:
                pass

            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()

            if stderr_text:
                logger.debug(f"CosyVoice stderr: {stderr_text[:500]}")

            if proc.returncode != 0:
                logger.error(f"CosyVoice process failed (rc={proc.returncode}): {stderr_text[:500]}")
                return b''

            # Find the OK:/FAIL: line (may have other output before it)
            ok_line = None
            for line in stdout_text.splitlines():
                if line.startswith("OK:") or line.startswith("FAIL:"):
                    ok_line = line
                    break

            if ok_line and ok_line.startswith("OK:"):
                # Read the WAV file
                with open(output_path, 'rb') as f:
                    wav_bytes = f.read()
                logger.info(f"CosyVoice output: {len(wav_bytes)} bytes")
                return wav_bytes
            else:
                logger.warning(f"CosyVoice produced no audio: {ok_line or stdout_text}")
                return b''

        finally:
            # Clean up temp WAV file
            try:
                os.unlink(output_path)
            except OSError:
                pass

    async def synthesize_streaming(self, text: str):
        """
        流式合成 - 逐块产出 WAV 音频数据
        使用 CosyVoice stream=True 模式，通过子进程生成多个音频块

        Args:
            text: 要合成的文本

        Yields:
            WAV格式的音频数据块 (bytes)
        """
        from typing import AsyncIterator

        logger.info(f"CosyVoice streaming synthesis: {text[:50]}...")

        # 创建临时目录存放音频块
        with tempfile.TemporaryDirectory() as tmp_dir:
            script = STREAMING_INFERENCE_SCRIPT.format(
                cosyvoice_dir=COSYVOICE_DIR,
                model_dir=self.model_dir,
                ref_audio=self.ref_audio,
                ref_text=self.ref_text,
                tts_text=text,
                output_dir=tmp_dir,
            )

            # 写入脚本到临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as script_file:
                script_file.write(script)
                script_path = script_file.name

            # 在 CosyVoice venv 的 Python 中运行
            proc = await asyncio.create_subprocess_exec(
                COSYVOICE_VENV_PYTHON, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.error("CosyVoice streaming process timed out")
                return

            # 清理脚本文件
            try:
                os.unlink(script_path)
            except OSError:
                pass

            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()

            if stderr_text:
                logger.debug(f"CosyVoice streaming stderr: {stderr_text[:500]}")

            if proc.returncode != 0:
                logger.error(f"CosyVoice streaming process failed (rc={proc.returncode}): {stderr_text[:500]}")
                return

            # 解析 "CHUNKS:N" 输出
            chunk_count = 0
            for line in stdout_text.splitlines():
                if line.startswith("CHUNKS:"):
                    chunk_count = int(line.split(":")[1])
                    break

            if chunk_count == 0:
                logger.warning(f"CosyVoice streaming produced no audio: {stdout_text}")
                return

            logger.info(f"CosyVoice streaming produced {chunk_count} chunks")

            # 按顺序读取音频块
            for i in range(chunk_count):
                chunk_path = os.path.join(tmp_dir, f"chunk_{i:04d}.wav")
                if os.path.exists(chunk_path):
                    with open(chunk_path, 'rb') as f:
                        yield f.read()

    async def synthesize_to_file(self, text: str, output_path: str):
        wav_bytes = await self.synthesize(text)
        with open(output_path, 'wb') as f:
            f.write(wav_bytes)
        logger.info(f"Audio saved to {output_path}")