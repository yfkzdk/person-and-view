import { create } from 'zustand'

interface RoleState {
  currentRole: string
  isSpeaking: boolean
  setCurrentRole: (role: string) => void
  setIsSpeaking: (speaking: boolean) => void
}

export const useRoleStore = create<RoleState>((set) => ({
  currentRole: 'companion',
  isSpeaking: false,
  setCurrentRole: (role) => set({ currentRole: role }),
  setIsSpeaking: (speaking) => set({ isSpeaking: speaking })
}))