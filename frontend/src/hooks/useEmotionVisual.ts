// frontend/src/hooks/useEmotionVisual.ts
import { useMemo } from 'react'
import { PADDimensions, FineEmotion } from '@/types/emotion'
import * as THREE from 'three'

/**
 * 将PAD维度映射到RGB颜色
 * Pleasure: 红-绿轴
 * Arousal: 亮度轴
 * Dominance: 蓝-黄轴
 */
function padToColor(pad: PADDimensions): THREE.Color {
  const { pleasure, arousal, dominance } = pad

  // 将-1到1映射到0到1
  const r = (pleasure + 1) / 2
  const g = (1 - Math.abs(pleasure)) * 0.5
  const b = (dominance + 1) / 2

  // 亮度基于arousal
  const brightness = 0.5 + arousal * 0.3

  const color = new THREE.Color(r * brightness, g * brightness, b * brightness)
  return color
}

/**
 * 将情绪家族映射到基础颜色
 */
const FAMILY_COLORS: Record<string, string> = {
  joy: '#fbbf24',        // 金黄色
  trust: '#10b981',      // 绿色
  fear: '#6366f1',       // 紫色
  surprise: '#f59e0b',   // 橙色
  sadness: '#3b82f6',    // 蓝色
  disgust: '#84cc16',    // 黄绿色
  anger: '#ef4444',      // 红色
  anticipation: '#8b5cf6', // 紫罗兰
  love: '#ec4899',       // 粉色
  optimism: '#14b8a6',   // 青色
  anxiety: '#a855f7',    // 紫色
  neutral: '#6b7280'     // 灰色
}

export function useEmotionVisual(emotion: FineEmotion | null) {
  return useMemo(() => {
    if (!emotion) {
      return {
        color: new THREE.Color('#6b7280'),
        intensity: 0.5,
        particleCount: 100,
        animationSpeed: 0.5
      }
    }

    // 基于PAD维度计算颜色
    const padColor = padToColor(emotion.padDimensions)

    // 基于情绪家族获取基础颜色
    const familyColor = new THREE.Color(FAMILY_COLORS[emotion.family] || '#6b7280')

    // 混合PAD颜色和家族颜色
    const finalColor = padColor.lerp(familyColor, 0.3)

    // 基于强度等级计算粒子数量和动画速度
    const intensityMap = { 1: 0.3, 2: 0.6, 3: 1.0 }
    const intensity = intensityMap[emotion.intensityLevel]

    const particleCount = Math.floor(100 + intensity * 200)
    const animationSpeed = 0.5 + intensity * 0.5

    return {
      color: finalColor,
      intensity,
      particleCount,
      animationSpeed
    }
  }, [emotion])
}
