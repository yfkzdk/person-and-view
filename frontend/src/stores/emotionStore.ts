import { create } from 'zustand'
import { FineEmotion, PADDimensions } from '@/types/emotion'

interface Emotion {
  type: string
  intensity: number
  label: string
  padDimensions?: PADDimensions
  family?: string
  intensityLevel?: 1 | 2 | 3
}

interface EmotionHistory {
  type: string
  timestamp: number
  intensity: number
  padDimensions?: PADDimensions
}

interface EmotionState {
  currentEmotion: Emotion
  emotionHistory: EmotionHistory[]
  setCurrentEmotion: (emotion: Emotion) => void
  addEmotionToHistory: (emotion: EmotionHistory) => void
  clearHistory: () => void
}

export const useEmotionStore = create<EmotionState>((set) => ({
  currentEmotion: {
    type: 'neutral',
    intensity: 0.5,
    label: '平静',
    padDimensions: {
      pleasure: 0,
      arousal: 0,
      dominance: 0
    },
    family: 'neutral',
    intensityLevel: 1
  },
  emotionHistory: [],

  setCurrentEmotion: (emotion) => set({ currentEmotion: emotion }),

  addEmotionToHistory: (emotion) =>
    set((state) => ({
      emotionHistory: [...state.emotionHistory.slice(-19), emotion] // 保留最近20条
    })),

  clearHistory: () => set({ emotionHistory: [] })
}))
