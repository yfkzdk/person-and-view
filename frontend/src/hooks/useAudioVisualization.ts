// frontend/src/hooks/useAudioVisualization.ts
/**
 * 音频可视化Hook - 优化版（使用AudioWorklet）
 * 参考: web-audio-samples-main/src/audio-worklet/
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { AudioVisualizationData } from '@/types/emotion'

export function useAudioVisualization(audioElement: HTMLAudioElement | null) {
  const [audioData, setAudioData] = useState<AudioVisualizationData>({
    waveform: [],
    frequency: [],
    volume: 0,
    isPlaying: false
  })

  const analyserRef = useRef<AnalyserNode | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [useWorklet, setUseWorklet] = useState(true)

  // 初始化Web Audio API（带AudioWorklet支持）
  const initializeAudio = useCallback(async () => {
    if (!audioElement || audioContextRef.current) return true

    try {
      // 检查浏览器支持
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!AudioContextClass) {
        throw new Error('Web Audio API not supported')
      }

      const audioContext = new AudioContextClass()
      const analyser = audioContext.createAnalyser()
      const source = audioContext.createMediaElementSource(audioElement)

      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8

      // 尝试加载AudioWorklet
      try {
        await audioContext.audioWorklet.addModule('/worklets/audio-analyzer-processor.js')

        // 创建AudioWorklet节点
        const workletNode = new AudioWorkletNode(audioContext, 'audio-analyzer-processor')

        // 监听来自worklet的消息
        workletNode.port.onmessage = (event) => {
          if (event.data.type === 'audioData') {
            setAudioData({
              waveform: event.data.waveform,
              frequency: event.data.frequency,
              volume: event.data.volume,
              isPlaying: audioElement?.paused === false
            })
          }
        }

        // 连接节点：source -> worklet -> analyser -> destination
        source.connect(workletNode)
        workletNode.connect(analyser)
        analyser.connect(audioContext.destination)

        workletNodeRef.current = workletNode
        setUseWorklet(true)

        console.log('AudioWorklet initialized successfully')
      } catch (workletError) {
        console.warn('AudioWorklet not available, falling back to main thread:', workletError)

        // Fallback: 使用传统的AnalyserNode
        source.connect(analyser)
        analyser.connect(audioContext.destination)
        setUseWorklet(false)
      }

      audioContextRef.current = audioContext
      analyserRef.current = analyser
      sourceRef.current = source
      setError(null)
      return true
    } catch (error) {
      console.error('Failed to initialize audio context:', error)
      setError(error instanceof Error ? error : new Error(String(error)))
      return false
    }
  }, [audioElement])

  // 主线程分析（fallback）
  const analyzeAudioMainThread = useCallback(() => {
    if (!analyserRef.current) return

    const analyser = analyserRef.current
    const bufferLength = analyser.frequencyBinCount

    // 波形数据
    const waveformArray = new Uint8Array(bufferLength)
    analyser.getByteTimeDomainData(waveformArray)

    // 频谱数据
    const frequencyArray = new Uint8Array(bufferLength)
    analyser.getByteFrequencyData(frequencyArray)

    // 计算音量
    const volume = frequencyArray.reduce((sum, value) => sum + value, 0) / bufferLength / 255

    setAudioData({
      waveform: Array.from(waveformArray).map(v => v / 128 - 1),
      frequency: Array.from(frequencyArray).map(v => v / 255),
      volume,
      isPlaying: audioElement?.paused === false
    })
  }, [audioElement])

  // 开始可视化
  const startVisualization = useCallback(async () => {
    if (!audioContextRef.current) {
      await initializeAudio()
    }

    if (audioContextRef.current?.state === 'suspended') {
      await audioContextRef.current.resume()
    }

    // 如果使用fallback模式，需要手动轮询
    if (!useWorklet && analyserRef.current) {
      const poll = () => {
        analyzeAudioMainThread()
        requestAnimationFrame(poll)
      }
      poll()
    }
  }, [initializeAudio, useWorklet, analyzeAudioMainThread])

  // 停止可视化
  const stopVisualization = useCallback(() => {
    // AudioWorklet会自动停止，无需手动处理
    // Fallback模式的requestAnimationFrame会在组件卸载时自动清理
  }, [])

  // 清理
  useEffect(() => {
    return () => {
      stopVisualization()
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [stopVisualization])

  return {
    audioData,
    startVisualization,
    stopVisualization,
    error,
    isUsingWorklet: useWorklet
  }
}
