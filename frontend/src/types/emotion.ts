// frontend/src/types/emotion.ts

/**
 * PAD三维情绪维度
 */
export interface PADDimensions {
  pleasure: number   // -1 to 1
  arousal: number    // -1 to 1
  dominance: number  // -1 to 1
}

/**
 * 细粒度情绪类型
 */
export interface FineEmotion {
  type: string           // 情绪类型ID (e.g., 'joy', 'sadness')
  value: string          // 中文标签 (e.g., '喜悦', '悲伤')
  family: string         // 情绪家族 (e.g., 'joy', 'sadness')
  intensityLevel: 1 | 2 | 3  // 强度等级
  padDimensions: PADDimensions
}

/**
 * 丰富情绪状态
 */
export interface RichEmotionState {
  primaryEmotion: FineEmotion
  intensity: number      // 0.0 to 1.0
  confidence: number     // 0.0 to 1.0
  secondaryEmotions?: Record<string, number>  // 次要情绪及权重
}

/**
 * 聊天消息
 */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  emotion?: RichEmotionState
  isTyping?: boolean
}

/**
 * 音频可视化数据
 */
export interface AudioVisualizationData {
  waveform: number[]      // 波形数据
  frequency: number[]     // 频谱数据
  volume: number          // 音量 0-1
  isPlaying: boolean
}