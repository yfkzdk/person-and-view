"""
TTS 性能测试（使用统一函数接口）
"""
import pytest
import asyncio
import time
from src.tts.tts_streamer import get_tts_audio, get_tts_format
from src.config import settings


@pytest.mark.asyncio
@pytest.mark.skip(reason="需要网络且耗时较长，CI 中跳过，本地手动运行")
async def test_tts_first_chunk_latency():
    """测试首字延迟"""
    text = "你好世界"
    start = time.perf_counter()
    first_chunk_time = None

    async for chunk in get_tts_audio(text):
        if first_chunk_time is None:
            first_chunk_time = time.perf_counter() - start
            break

    print(f"\nTTS First Chunk Latency: {first_chunk_time * 1000:.2f} ms")
    assert first_chunk_time < 5.0, f"First chunk latency {first_chunk_time}s exceeds 5s"


@pytest.mark.asyncio
@pytest.mark.skip(reason="需要网络且耗时较长")
async def test_tts_throughput():
    """测试 TTS 吞吐量"""
    text = "这是一个测试文本。" * 10
    start = time.perf_counter()
    chunk_count = 0

    async for chunk in get_tts_audio(text):
        chunk_count += 1

    duration = time.perf_counter() - start
    print(f"\nTTS Throughput: chunks={chunk_count}, duration={duration:.2f}s")
