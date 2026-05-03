'use client'

interface CharacterSelectorProps {
  characters: string[]
  currentCharacter: string
  onSelect: (name: string) => void
}

export function CharacterSelector({ characters, currentCharacter, onSelect }: CharacterSelectorProps) {
  if (characters.length <= 1) return null

  return (
    <select
      value={currentCharacter}
      onChange={(e) => onSelect(e.target.value)}
      className="aurora-select px-3 py-1.5 text-xs"
      style={{ borderRadius: '10px' }}
    >
      {characters.map((name) => (
        <option key={name} value={name} style={{ background: '#14002b', color: '#ede4f7' }}>
          {name}
        </option>
      ))}
    </select>
  )
}
