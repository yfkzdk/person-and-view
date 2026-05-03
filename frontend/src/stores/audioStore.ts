import { create } from 'zustand'
import { AudioVisualizationData } from '@/types/emotion'

interface AudioState {
  audioData: AudioVisualizationData
  isPlaying: boolean
  setAudioData: (data: Partial<AudioVisualizationData>) => void
  setIsPlaying: (playing: boolean) => void
}

export const useAudioStore = create<AudioState>((set) => ({
  audioData: {
    waveform: [],
    frequency: [],
    volume: 0,
    isPlaying: false
  },
  isPlaying: false,
  setAudioData: (data) =>
    set((state) => ({
      audioData: { ...state.audioData, ...data }
    })),
  setIsPlaying: (playing) => set({ isPlaying: playing })
}))