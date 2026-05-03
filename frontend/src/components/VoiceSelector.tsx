'use client'

interface VoiceSelectorProps {
  voices: string[]
  currentVoice: string
  onSelect: (name: string) => void
}

export function VoiceSelector({ voices, currentVoice, onSelect }: VoiceSelectorProps) {
  if (voices.length <= 1) return null

  return (
    <select
      value={currentVoice}
      onChange={(e) => onSelect(e.target.value)}
      className="aurora-select px-3 py-1.5 text-xs"
      style={{ borderRadius: '10px' }}
    >
      {voices.map((name) => (
        <option key={name} value={name} style={{ background: '#14002b', color: '#ede4f7' }}>
          {name}
        </option>
      ))}
    </select>
  )
}
