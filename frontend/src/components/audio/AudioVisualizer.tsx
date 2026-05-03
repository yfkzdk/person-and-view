// frontend/src/components/audio/AudioVisualizer.tsx
'use client'

import { useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useAudioVisualization } from '@/hooks/useAudioVisualization'

interface AudioVisualizerProps {
  audioUrl?: string
  className?: string
}

export function AudioVisualizer({ audioUrl, className = '' }: AudioVisualizerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)

  const { audioData, startVisualization, stopVisualization, error } = useAudioVisualization(audioElement)

  // 绘制波形
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const { waveform, frequency, volume } = audioData

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 绘制频谱条
    const barWidth = canvas.width / frequency.length
    const centerY = canvas.height / 2

    frequency.forEach((value, index) => {
      const x = index * barWidth
      const height = value * canvas.height * 0.8
      const hue = (index / frequency.length) * 360

      ctx.fillStyle = `hsla(${hue}, 70%, 60%, ${0.3 + volume * 0.7})`
      ctx.fillRect(x, centerY - height / 2, barWidth - 1, height)
    })

    // 绘制波形线
    ctx.beginPath()
    ctx.strokeStyle = `rgba(255, 255, 255, ${0.5 + volume * 0.5})`
    ctx.lineWidth = 2

    waveform.forEach((value, index) => {
      const x = (index / waveform.length) * canvas.width
      const y = centerY + value * canvas.height * 0.3

      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })

    ctx.stroke()
  }, [audioData])

  const handlePlay = () => {
    if (audioRef.current) {
      audioRef.current.play()
      startVisualization()
    }
  }

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      stopVisualization()
    }
  }

  return (
    <div className={`relative ${className}`}>
      {/* 音频元素 */}
      {audioUrl && (
        <audio
          ref={(el) => {
            audioRef.current = el
            setAudioElement(el)
          }}
          src={audioUrl}
          onPlay={startVisualization}
          onPause={stopVisualization}
          onEnded={stopVisualization}
          className="hidden"
        />
      )}

      {/* Error display */}
      {error && (
        <div className="absolute top-4 left-4 px-4 py-2 bg-red-500 text-white rounded-lg">
          {error.message}
        </div>
      )}

      {/* 可视化画布 */}
      <motion.canvas
        ref={canvasRef}
        width={800}
        height={200}
        className="w-full h-48 rounded-lg bg-gradient-to-b from-gray-900 to-gray-800"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      />

      {/* 控制按钮 */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-4">
        <motion.button
          onClick={handlePlay}
          className="px-6 py-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition-colors"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          播放
        </motion.button>

        <motion.button
          onClick={handlePause}
          className="px-6 py-2 bg-gray-600 text-white rounded-full hover:bg-gray-700 transition-colors"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          暂停
        </motion.button>
      </div>

      {/* 音量指示器 */}
      <div className="absolute top-4 right-4">
        <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-green-400 to-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${audioData.volume * 100}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
      </div>
    </div>
  )
}
