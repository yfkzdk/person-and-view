"""
VAD 性能测试
"""
import pytest
import numpy as np
import time
from src.vad.vad_monitor import VADMonitor


def test_vad_latency():
    """测试 VAD 延迟"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成测试音频（512 samples for 16kHz）
    audio = np.random.randn(512).astype(np.float32)

    # 预热
    for _ in range(10):
        monitor.detect_speech(audio)

    # 测试延迟
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        monitor.detect_speech(audio)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms

    avg_latency = np.mean(latencies)
    max_latency = np.max(latencies)

    print(f"\nVAD Latency:")
    print(f"  Average: {avg_latency:.3f} ms")
    print(f"  Max: {max_latency:.3f} ms")
    print(f"  Min: {np.min(latencies):.3f} ms")

    # 验证延迟 < 1ms
    assert avg_latency < 1.0, f"Average latency {avg_latency}ms exceeds 1ms"
    assert max_latency < 2.0, f"Max latency {max_latency}ms exceeds 2ms"


def test_vad_throughput():
    """测试 VAD 吞吐量"""
    monitor = VADMonitor(sample_rate=16000, threshold=0.5)

    # 生成测试音频（512 samples）
    audio = np.random.randn(512).astype(np.float32)

    # 测试吞吐量
    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        monitor.detect_speech(audio)
    end = time.perf_counter()

    total_time = end - start
    throughput = iterations / total_time

    print(f"\nVAD Throughput:")
    print(f"  {throughput:.2f} calls/second")
    print(f"  {throughput * 512 / 1000:.2f} kSamples/second")

    # 验证吞吐量
    assert throughput > 100, "Throughput too low"