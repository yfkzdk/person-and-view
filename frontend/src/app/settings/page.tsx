'use client'

import { useState, useEffect, useCallback } from 'react'

/* ================================================================
   Character Management Page — CRUD operations via REST API
   ================================================================ */

interface Character {
  name: string
  description: string
  personality: string
  scenario: string
  first_mes: string
  tags: string[]
  system_prompt_preview: string
}

export default function CharacterSettings() {
  const [characters, setCharacters] = useState<string[]>([])
  const [selected, setSelected] = useState<Character | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  // New character form
  const [form, setForm] = useState({
    name: '', description: '', personality: '', scenario: '',
    first_mes: '', system_prompt: '', tags: ''
  })

  const API = 'http://localhost:8765/api/characters'

  // ── Fetch character list ──
  const fetchCharacters = useCallback(async () => {
    try {
      const res = await fetch(API + '/')
      if (res.ok) setCharacters(await res.json())
    } catch { setError('Cannot connect to server') }
  }, [])

  useEffect(() => { fetchCharacters() }, [fetchCharacters])

  // ── Select character ──
  const selectCharacter = async (name: string) => {
    setError('')
    try {
      const res = await fetch(`${API}/${name}`)
      if (res.ok) setSelected(await res.json())
      else setError(await res.text())
    } catch { setError('Failed to load character') }
  }

  // ── Create ──
  const handleCreate = async () => {
    if (!form.name.trim()) return
    setError('')
    setLoading(true)
    try {
      const res = await fetch(API + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          personality: form.personality,
          scenario: form.scenario,
          first_mes: form.first_mes,
          system_prompt: form.system_prompt,
          tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
        })
      })
      if (res.ok) {
        setShowCreate(false)
        setForm({ name: '', description: '', personality: '', scenario: '', first_mes: '', system_prompt: '', tags: '' })
        await fetchCharacters()
      } else setError(await res.text())
    } catch { setError('Create failed') }
    finally { setLoading(false) }
  }

  // ── Delete ──
  const handleDelete = async (name: string) => {
    if (!confirm(`Delete character "${name}"? This cannot be undone.`)) return
    setError('')
    try {
      const res = await fetch(`${API}/${name}`, { method: 'DELETE' })
      if (res.ok) {
        setSelected(null)
        await fetchCharacters()
      } else setError(await res.text())
    } catch { setError('Delete failed') }
  }

  // ── Activate ──
  const handleActivate = async (name: string) => {
    setError('')
    try {
      const res = await fetch(`${API}/${name}/activate`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setError(`Switched to "${data.active_character}"`)
        setTimeout(() => setError(''), 2000)
      }
    } catch { setError('Activate failed') }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 p-6 font-mono">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-1">Character Manager</h1>
        <p className="text-zinc-500 mb-6 text-sm">Manage AI personalities — create, edit, delete, activate</p>

        {error && (
          <div className={`mb-4 px-4 py-2 rounded text-sm ${error.includes('Switched') ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Left: Character List */}
          <div className="md:col-span-1 bg-zinc-900 rounded-lg p-4 border border-zinc-800">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Characters ({characters.length})</h2>
              <button onClick={() => setShowCreate(!showCreate)} className="text-xs px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300">
                {showCreate ? 'Cancel' : '+ New'}
              </button>
            </div>

            {/* Create Form */}
            {showCreate && (
              <div className="mb-4 p-3 bg-zinc-800 rounded space-y-2">
                <input className="w-full bg-zinc-700 px-2 py-1 rounded text-sm" placeholder="Name *" value={form.name}
                  onChange={e => setForm({...form, name: e.target.value})} />
                <input className="w-full bg-zinc-700 px-2 py-1 rounded text-sm" placeholder="Description"
                  value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
                <input className="w-full bg-zinc-700 px-2 py-1 rounded text-sm" placeholder="Personality (e.g. 幽默、理性)"
                  value={form.personality} onChange={e => setForm({...form, personality: e.target.value})} />
                <input className="w-full bg-zinc-700 px-2 py-1 rounded text-sm" placeholder="Tags (comma separated)"
                  value={form.tags} onChange={e => setForm({...form, tags: e.target.value})} />
                <input className="w-full bg-zinc-700 px-2 py-1 rounded text-sm" placeholder="First message"
                  value={form.first_mes} onChange={e => setForm({...form, first_mes: e.target.value})} />
                <textarea className="w-full bg-zinc-700 px-2 py-1 rounded text-sm h-20" placeholder="System prompt"
                  value={form.system_prompt} onChange={e => setForm({...form, system_prompt: e.target.value})} />
                <button onClick={handleCreate} disabled={loading || !form.name.trim()}
                  className="w-full py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 rounded text-sm font-medium">
                  {loading ? 'Creating...' : 'Create Character'}
                </button>
              </div>
            )}

            {/* List */}
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {characters.map(name => (
                <button key={name} onClick={() => selectCharacter(name)}
                  className={`w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between
                    ${selected?.name === name ? 'bg-zinc-700 text-white' : 'hover:bg-zinc-800 text-zinc-400'}`}>
                  <span>{name}</span>
                  <span className="text-[10px] text-zinc-600">→</span>
                </button>
              ))}
              {characters.length === 0 && <p className="text-zinc-600 text-sm p-2">No characters yet</p>}
            </div>
          </div>

          {/* Right: Detail */}
          <div className="md:col-span-2 bg-zinc-900 rounded-lg p-5 border border-zinc-800">
            {selected ? (
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold">{selected.name}</h2>
                    <p className="text-zinc-400 text-sm mt-1">{selected.description}</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleActivate(selected.name)}
                      className="px-3 py-1.5 text-xs rounded bg-blue-800 hover:bg-blue-700 text-blue-200">
                      Activate
                    </button>
                    <button onClick={() => handleDelete(selected.name)}
                      className="px-3 py-1.5 text-xs rounded bg-red-900 hover:bg-red-800 text-red-300">
                      Delete
                    </button>
                  </div>
                </div>

                {selected.tags && selected.tags.length > 0 && (
                  <div className="flex gap-1.5 mb-4 flex-wrap">
                    {selected.tags.map(tag => (
                      <span key={tag} className="px-2 py-0.5 text-[10px] rounded-full bg-zinc-800 text-zinc-400">{tag}</span>
                    ))}
                  </div>
                )}

                <div className="space-y-3">
                  <Field label="Personality" value={selected.personality} />
                  <Field label="Scenario" value={selected.scenario} />
                  <Field label="First Message" value={selected.first_mes} />
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">System Prompt</span>
                    <pre className="mt-1 p-3 bg-zinc-950 rounded text-xs text-zinc-400 whitespace-pre-wrap max-h-60 overflow-y-auto">
                      {selected.system_prompt_preview}
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-64 text-zinc-600 text-sm">
                Select a character to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div>
      <span className="text-[10px] text-zinc-500 uppercase tracking-wider">{label}</span>
      <p className="text-sm text-zinc-300 mt-1">{value}</p>
    </div>
  )
}
