'use client'

import { useEffect, useRef, useCallback } from 'react'
import { useAudioStore } from '@/stores/audioStore'

export function useAudioProcessing() {
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)

  const { setAudioData, setIsPlaying } = useAudioStore()

  const initializeAudio = useCallback(async () => {
    try {
      // 创建音频上下文
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256

      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)

      console.log('Audio processing initialized')
    } catch (error) {
      console.error('Failed to initialize audio:', error)
    }
  }, [])

  const startAnalysis = useCallback(() => {
    if (!analyserRef.current) return

    const analyser = analyserRef.current
    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const analyze = () => {
      analyser.getByteFrequencyData(dataArray)

      // 计算音量
      const volume = Array.from(dataArray).reduce((sum, value) => sum + value, 0) / dataArray.length

      // 提取频率数据
      const frequency = Array.from(dataArray)

      setAudioData({
        volume: volume / 255, // 归一化到 0-1
        frequency: frequency.slice(0, 64) // 只取前64个频率点
      })

      animationFrameRef.current = requestAnimationFrame(analyze)
    }

    analyze()
    setIsPlaying(true)
  }, [setAudioData, setIsPlaying])

  const stopAnalysis = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    setIsPlaying(false)
    setAudioData({
      waveform: [],
      frequency: [],
      volume: 0,
      isPlaying: false
    })
  }, [setIsPlaying, setAudioData])

  const cleanup = useCallback(() => {
    stopAnalysis()
    if (audioContextRef.current) {
      audioContextRef.current.close()
    }
  }, [stopAnalysis])

  useEffect(() => {
    return () => cleanup()
  }, [cleanup])

  return {
    initializeAudio,
    startAnalysis,
    stopAnalysis,
    cleanup
  }
}