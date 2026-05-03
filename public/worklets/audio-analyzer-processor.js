// public/worklets/audio-analyzer-processor.js
/**
 * AudioWorklet处理器 - 音频分析
 * 参考: web-audio-samples-main/src/audio-worklet/basic/hello-audio-worklet/
 *
 * 在独立线程中处理音频分析，避免阻塞主线程
 */

class AudioAnalyzerProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.bufferSize = 256
    this.buffer = new Float32Array(this.bufferSize)
    this.bufferIndex = 0
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0]

    if (input.length > 0) {
      const channelData = input[0] // 使用第一个声道

      // 累积数据到缓冲区
      for (let i = 0; i < channelData.length; i++) {
        this.buffer[this.bufferIndex++] = channelData[i]

        // 缓冲区满时发送数据
        if (this.bufferIndex >= this.bufferSize) {
          // 计算波形数据（下采样到128个点）
          const waveform = this.calculateWaveform(this.buffer)

          // 计算频谱数据（简化版RMS）
          const frequency = this.calculateFrequency(this.buffer)

          // 计算音量
          const volume = this.calculateVolume(this.buffer)

          // 发送到主线程
          this.port.postMessage({
            type: 'audioData',
            waveform,
            frequency,
            volume
          })

          // 重置缓冲区
          this.bufferIndex = 0
        }
      }
    }

    return true
  }

  /**
   * 计算波形数据（下采样）
   */
  calculateWaveform(buffer) {
    const samples = 128
    const step = Math.floor(buffer.length / samples)
    const waveform = new Float32Array(samples)

    for (let i = 0; i < samples; i++) {
      let sum = 0
      for (let j = 0; j < step; j++) {
        sum += buffer[i * step + j]
      }
      waveform[i] = sum / step
    }

    return Array.from(waveform)
  }

  /**
   * 计算频谱数据（简化版，使用RMS）
   */
  calculateFrequency(buffer) {
    const samples = 128
    const step = Math.floor(buffer.length / samples)
    const frequency = new Float32Array(samples)

    for (let i = 0; i < samples; i++) {
      let rms = 0
      for (let j = 0; j < step; j++) {
        const value = buffer[i * step + j]
        rms += value * value
      }
      frequency[i] = Math.sqrt(rms / step)
    }

    // 归一化到0-1
    const max = Math.max(...frequency)
    if (max > 0) {
      for (let i = 0; i < frequency.length; i++) {
        frequency[i] /= max
      }
    }

    return Array.from(frequency)
  }

  /**
   * 计算音量（RMS）
   */
  calculateVolume(buffer) {
    let sum = 0
    for (let i = 0; i < buffer.length; i++) {
      sum += buffer[i] * buffer[i]
    }
    return Math.sqrt(sum / buffer.length)
  }
}

registerProcessor('audio-analyzer-processor', AudioAnalyzerProcessor)
