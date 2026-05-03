'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { NeuralCulture } from '@/components/emotion/EmotionVisualizer'
import type { Emotion, DissolveEvent } from '@/components/emotion/EmotionVisualizer'

/* ================================================================
   Types
   ================================================================ */

interface Message {
  role: 'user' | 'assistant'
  content: string
  audioUrl?: string
  emotionWeights?: Record<string, number>
}

type MicState = 'idle' | 'recording' | 'responding'

/* ================================================================
   Markdown renderer (simple inline)
   ================================================================ */

function renderMarkdown(text: string): string {
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/`(.+?)`/g, '<code class="inline-code">$1</code>')
  html = html.replace(/\n/g, '<br/>')
  return html
}

/* ================================================================
   Emotion-weighted text glow builder
   ================================================================ */

const EMOTION_COLORS: Record<string, string> = {
  happy: 'rgba(255,221,0,',
  calm: 'rgba(160,240,160,',
  sad: 'rgba(122,106,192,',
  angry: 'rgba(255,85,0,',
  excited: 'rgba(0,238,255,',
  curious: 'rgba(155,93,229,',
  tense: 'rgba(255,107,157,',
  neutral: 'rgba(176,192,208,',
}

function buildTextShadow(weights?: Record<string, number>): string {
  if (!weights) return '0 0 8px rgba(0,255,200,0.2)'
  const shadows: string[] = []
  for (const [emo, w] of Object.entries(weights)) {
    const color = EMOTION_COLORS[emo] || EMOTION_COLORS.neutral
    if (w > 0.05) shadows.push(`0 0 ${(w * 20).toFixed(1)}px ${color}${(w * 0.5).toFixed(2)})`)
  }
  return shadows.length > 0 ? shadows.join(', ') : '0 0 8px rgba(0,255,200,0.2)'
}

function buildTextColor(weights?: Record<string, number>): string {
  if (!weights) return 'var(--bio-text)'
  let r = 0, g = 0, b = 0, total = 0
  const hexMap: Record<string, [number, number, number]> = {
    happy: [255, 221, 0], calm: [160, 240, 160], sad: [122, 106, 192],
    angry: [255, 85, 0], excited: [0, 238, 255], curious: [155, 93, 229],
    tense: [255, 107, 157], neutral: [176, 192, 208],
  }
  for (const [emo, w] of Object.entries(weights)) {
    const [hr, hg, hb] = hexMap[emo] || hexMap.neutral
    r += hr * w; g += hg * w; b += hb * w; total += w
  }
  if (total === 0) return 'var(--bio-text)'
  return `rgb(${Math.round(r/total)},${Math.round(g/total)},${Math.round(b/total)})`
}

/* ================================================================
   Character Pill
   ================================================================ */

function CharacterPill({ name, isActive, onClick }: { name: string; isActive: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`char-pill ${isActive ? 'active' : ''}`}>
      <span className="char-pill-dot" />
      {name}
    </button>
  )
}

/* ================================================================
   Main Page
   ================================================================ */

export default function Home() {
  // ---- State ----
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isConnected, setWsConnected] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [currentCharacter, setCurrentCharacter] = useState('童锦程')
  const [connectionStatus, setConnectionStatus] = useState<string>('未连接')
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [audioVolume, setAudioVolume] = useState(0)
  const [characters, setCharacters] = useState<string[]>([currentCharacter])
  const [voiceMode, setVoiceMode] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [emotionWeights, setEmotionWeights] = useState<Record<string, number>>({ neutral: 1 })
  const [derivedEmotion, setDerivedEmotion] = useState<Emotion>('neutral')
  const [micState, setMicState] = useState<MicState>('idle')
  const [voiceError, setVoiceError] = useState<string>('')
  const [dissolvingIds, setDissolvingIds] = useState<Set<number>>(new Set())

  // ---- Refs ----
  const wsRef = useRef<WebSocket | null>(null)
  const audioFormatRef = useRef<string>('mp3')
  const audioChunksRef = useRef<Uint8Array[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messageRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const sessionIdRef = useRef<string>('session_' + Math.random().toString(36).substring(2, 9))
  const currentAssistantIdxRef = useRef<number>(-1)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const animFrameRef = useRef<number>(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const recognitionRef = useRef<any>(null)
  const voiceModeRef = useRef(false)
  const isConnectedRef = useRef(false)
  const isProcessingRef = useRef(false)
  const dissolveEventRef = useRef<DissolveEvent | null>(null)

  // Sync refs
  useEffect(() => { voiceModeRef.current = voiceMode }, [voiceMode])
  useEffect(() => { isConnectedRef.current = isConnected }, [isConnected])
  useEffect(() => { isProcessingRef.current = isProcessing }, [isProcessing])

  // Derive mic state
  useEffect(() => {
    if (isRecording) setMicState('recording')
    else if (isProcessing || isAudioPlaying) setMicState('responding')
    else setMicState('idle')
  }, [isRecording, isProcessing, isAudioPlaying])

  // ---- Auto-scroll ----
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ---- Audio analysis ----
  const startAudioAnalysis = useCallback((audio: HTMLAudioElement) => {
    if (!audioCtxRef.current) audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
    const ctx = audioCtxRef.current
    if (ctx.state === 'suspended') ctx.resume()
    if (!analyserRef.current) {
      analyserRef.current = ctx.createAnalyser()
      analyserRef.current.fftSize = 64
      analyserRef.current.smoothingTimeConstant = 0.7
    }
    try { const source = ctx.createMediaElementSource(audio); source.connect(analyserRef.current); analyserRef.current.connect(ctx.destination) } catch {}
    const analyser = analyserRef.current
    const dataArray = new Uint8Array(analyser.frequencyBinCount)
    const loop = () => { analyser.getByteFrequencyData(dataArray); setAudioVolume(dataArray.reduce((a, b) => a + b, 0) / dataArray.length / 255); animFrameRef.current = requestAnimationFrame(loop) }
    loop()
  }, [])

  const stopAudioAnalysis = useCallback(() => {
    if (animFrameRef.current) { cancelAnimationFrame(animFrameRef.current); animFrameRef.current = 0 }
    setAudioVolume(0); setIsAudioPlaying(false)
  }, [])

  useEffect(() => { return () => { stopAudioAnalysis(); if (audioCtxRef.current) audioCtxRef.current.close() } }, [stopAudioAnalysis])

  // ---- Auto-play + voice mode resume ----
  const playAudio = useCallback((url: string) => {
    if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current = null }
    const audio = new Audio(url)
    currentAudioRef.current = audio
    audio.onplay = () => { setIsAudioPlaying(true); startAudioAnalysis(audio) }
    audio.onended = () => { setIsAudioPlaying(false); stopAudioAnalysis(); if (voiceModeRef.current && isConnectedRef.current && !isProcessingRef.current) setTimeout(() => startSpeechRecognition(), 700) }
    audio.onpause = () => { setIsAudioPlaying(false); stopAudioAnalysis() }
    audio.play().catch(console.error)
  }, [startAudioAnalysis, stopAudioAnalysis])

  useEffect(() => {
    const lastMsg = messages[messages.length - 1]
    if (lastMsg?.audioUrl && lastMsg.role === 'assistant') playAudio(lastMsg.audioUrl)
  }, [messages, playAudio])

  // ---- Derive emotion from weights ----
  useEffect(() => {
    const weights = emotionWeights
    if (!weights || Object.keys(weights).length === 0) { setDerivedEmotion('neutral'); return }
    const top = Object.entries(weights).sort((a, b) => b[1] - a[1])[0]?.[0]
    const map: Record<string, Emotion> = { happy: 'happy', calm: 'calm', sad: 'sad', angry: 'angry', excited: 'excited', curious: 'neutral', tense: 'angry', neutral: 'neutral' }
    setDerivedEmotion(map[top] || 'neutral')
  }, [emotionWeights])

  // ---- Idle → neutral decay ----
  useEffect(() => {
    if (!isAudioPlaying && !isProcessing) {
      const t = setTimeout(() => { if (!isAudioPlaying && !isProcessing) setEmotionWeights({ neutral: 1 }) }, 5000)
      return () => clearTimeout(t)
    }
  }, [isAudioPlaying, isProcessing])

  // ---- Speech Recognition ----
  const startSpeechRecognition = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) { setVoiceError('浏览器不支持语音，请用 Chrome/Edge'); return }
    setVoiceError('')

    // Interrupt any ongoing playback/generation
    if (currentAudioRef.current && !currentAudioRef.current.paused) {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'control', action: 'interrupt' }))
      }
      currentAudioRef.current.pause()
      currentAudioRef.current = null
      stopAudioAnalysis()
      setIsAudioPlaying(false)
      setIsProcessing(false)
    }

    const r = new SpeechRecognition(); r.lang = 'zh-CN'; r.continuous = true; r.interimResults = true
    r.onstart = () => { setIsRecording(true); setInterimText(''); setVoiceError('') }
    r.onresult = (e: any) => {
      let interim = ''; let final = ''
      for (let i = e.resultIndex; i < e.results.length; i++) { const t = e.results[i][0].transcript; if (e.results[i].isFinal) final += t; else interim += t }
      setInterimText(interim)
      if (final) { setInterimText(''); handleSendMessage(final) }
    }
    r.onerror = (e: any) => {
      setIsRecording(false); setInterimText('')
      if (e.error === 'no-speech') setVoiceError('未检测到语音，请再试一次')
      else if (e.error === 'aborted') setVoiceError('')
      else setVoiceError('识别出错: ' + (e.error || 'unknown'))
      if (voiceModeRef.current && isConnectedRef.current && !isProcessingRef.current) setTimeout(() => startSpeechRecognition(), 1500)
    }
    r.onend = () => { setIsRecording(false); setInterimText(''); if (voiceModeRef.current && isConnectedRef.current && !isProcessingRef.current) setTimeout(() => startSpeechRecognition(), 800) }
    recognitionRef.current = r; r.start()
  }, [])

  const stopSpeechRecognition = useCallback(() => {
    if (recognitionRef.current) { recognitionRef.current.stop(); recognitionRef.current = null }
    setIsRecording(false); setInterimText('')
  }, [])

  // ---- WebSocket message handler ----
  const handleWsMessage = useCallback((event: MessageEvent) => {
    if (typeof event.data !== 'string') return
    try {
      const msg = JSON.parse(event.data)
      switch (msg.type) {
        case 'text_chunk': {
          if (msg.is_final) setIsProcessing(false)
          if (msg.content) {
            setMessages(prev => {
              const idx = currentAssistantIdxRef.current
              if (idx >= 0 && idx < prev.length && prev[idx].role === 'assistant') {
                const u = [...prev]; u[idx] = { ...u[idx], content: u[idx].content + msg.content }; return u
              }
              currentAssistantIdxRef.current = prev.length
              return [...prev, { role: 'assistant', content: msg.content }]
            })
          }
          break
        }
        case 'audio':
          if (msg.format) audioFormatRef.current = msg.format
          if (msg.data) {
            const bytes = new Uint8Array(atob(msg.data).length); for (let i = 0; i < bytes.length; i++) bytes[i] = atob(msg.data).charCodeAt(i)
            if (msg.is_new_file) audioChunksRef.current = []
            audioChunksRef.current.push(bytes)
          }
          if (msg.is_final) {
            const mime = audioFormatRef.current === 'mp3' ? 'audio/mpeg' : `audio/${audioFormatRef.current}`
            const all = new Uint8Array(audioChunksRef.current.reduce((a, c) => a + c.length, 0)); let off = 0; for (const c of audioChunksRef.current) { all.set(c, off); off += c.length }
            const url = URL.createObjectURL(new Blob([all], { type: mime }))
            setMessages(prev => {
              const idx = currentAssistantIdxRef.current
              if (idx >= 0 && idx < prev.length && prev[idx].role === 'assistant') { const u = [...prev]; u[idx] = { ...u[idx], audioUrl: url }; return u }
              const last = prev.map((m, i) => m.role === 'assistant' ? i : -1).filter(i => i >= 0).pop()
              if (last !== undefined) { const u = [...prev]; u[last] = { ...u[last], audioUrl: url }; return u }
              return prev
            })
            audioChunksRef.current = []
          }
          break
        case 'emotion':
          if (msg.weights) setEmotionWeights(msg.weights)
          else if (msg.emotion) {
            const emap: Record<string, number> = { '开心': 1, 'happy': 1, '沮丧': 0.2, 'sad': 0.2, '愤怒': 0.1, 'angry': 0.1, '焦虑': 0.15, 'anxious': 0.15, '平静': 0.5, 'calm': 0.5, '兴奋': 0.4, 'excited': 0.4 }
            setEmotionWeights({ [msg.emotion]: emap[msg.emotion] || 0.5, neutral: 0.3 })
          }
          break
        case 'interrupted':
          setIsProcessing(false)
          currentAssistantIdxRef.current = -1
          stopAudioAnalysis()
          if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current = null }
          setIsAudioPlaying(false)
          break
        case 'status':
          if (msg.status === 'listening') { setIsProcessing(false); currentAssistantIdxRef.current = -1 }
          break
        case 'error':
          setIsProcessing(false); currentAssistantIdxRef.current = -1
          break
        case 'character_switched':
          if (msg.success) setCurrentCharacter(msg.character_name)
          break
        case 'character_info':
          if (msg.name) setCurrentCharacter(msg.name)
          break
        case 'character_list':
          if (msg.characters) setCharacters(msg.characters)
          break
        case 'heartbeat': break
      }
    } catch {}
  }, [])

  // ---- WebSocket connection ----
  const connectWebSocket = useCallback(() => {
    const sid = sessionIdRef.current; const port = parseInt(process.env.NEXT_PUBLIC_BACKEND_PORT || '8765', 10)
    let connected = false
    const tryConnect = () => {
      if (connected) return
      setConnectionStatus('正在连接...')
      const ws = new WebSocket(`ws://localhost:${port}/ws/${sid}`)
      const timeout = setTimeout(() => { if (!connected) ws.close() }, 5000)
      ws.onopen = () => { clearTimeout(timeout); connected = true; wsRef.current = ws; setWsConnected(true); setConnectionStatus('Online'); ws.send(JSON.stringify({ type: 'list_characters' })) }
      ws.onmessage = (e) => handleWsMessage(e)
      ws.onclose = () => { clearTimeout(timeout); if (connected) { connected = false; setWsConnected(false); setConnectionStatus('连接已断开'); wsRef.current = null } reconnectTimeoutRef.current = setTimeout(() => { connected = false; tryConnect() }, 3000) }
      ws.onerror = () => { clearTimeout(timeout); if (!connected) setConnectionStatus('无法连接') }
    }
    tryConnect()
    return () => { connected = true; if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current) }
  }, [handleWsMessage])

  useEffect(() => { const cleanup = connectWebSocket(); return cleanup }, [connectWebSocket])

  const handleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null }
    connectWebSocket()
  }, [connectWebSocket])

  // ---- Send ----
  const handleSendMessage = useCallback((text?: string) => {
    const content = (text || inputText).trim()
    if (!content || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setMessages(prev => [...prev, { role: 'user', content }])
    setInputText(''); setIsProcessing(true)
    setEmotionWeights({ neutral: 1 })
    currentAssistantIdxRef.current = -1
    wsRef.current.send(JSON.stringify({ type: 'text_input', content, session_id: sessionIdRef.current }))
  }, [inputText])

  // ---- Character switch ----
  const handleSwitchCharacter = useCallback((name: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'switch_character', character_name: name }))
  }, [])

  // ---- Voice mode toggle ----
  const toggleVoiceMode = useCallback(() => {
    setVoiceMode(prev => {
      const next = !prev
      if (next && isConnected && !isProcessing) setTimeout(() => startSpeechRecognition(), 300)
      if (!next) stopSpeechRecognition()
      return next
    })
  }, [isConnected, isProcessing, startSpeechRecognition, stopSpeechRecognition])

  const toggleFullscreen = useCallback(() => setIsFullscreen(prev => !prev), [])
  useEffect(() => { const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && isFullscreen) setIsFullscreen(false); if (e.key === 'v' && e.ctrlKey) { e.preventDefault(); toggleVoiceMode() } }; window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h) }, [isFullscreen, toggleVoiceMode])

  // ---- Text dissolution via IntersectionObserver ----
  const dissolvingIdsRef = useRef<Set<number>>(new Set())
  const messagesRef = useRef<Message[]>(messages)
  const observerRef = useRef<IntersectionObserver | null>(null)
  useEffect(() => { messagesRef.current = messages }, [messages])

  useEffect(() => {
    const scrollEl = document.querySelector('.messages-scroll')
    if (!scrollEl) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const idx = parseInt(entry.target.getAttribute('data-msg-idx') || '-1')
          if (idx < 0 || dissolvingIdsRef.current.has(idx)) return
          if (!entry.isIntersecting) {
            dissolvingIdsRef.current.add(idx)
            setDissolvingIds(new Set(dissolvingIdsRef.current))
            const msg = messagesRef.current[idx]
            if (msg) {
              dissolveEventRef.current = {
                type: msg.role === 'user' ? 'user_message' : 'assistant_message',
                count: 1,
              }
            }
            setTimeout(() => {
              dissolvingIdsRef.current.delete(idx)
              setDissolvingIds(new Set(dissolvingIdsRef.current))
            }, 1600)
          }
        })
      },
      { root: scrollEl, rootMargin: '0px 0px -40px 0px', threshold: 0.1 }
    )

    observerRef.current = observer
    // Observe existing elements
    messageRefs.current.forEach(el => observer.observe(el))

    return () => observer.disconnect()
  }, [])

  // Re-observe when new messages appear
  useEffect(() => {
    if (observerRef.current) {
      messageRefs.current.forEach(el => {
        try { observerRef.current?.observe(el) } catch {}
      })
    }
  }, [messages])

  // ---- Keyboard ----
  const handleRecordingStart = useCallback(() => {}, [])
  const handleRecordingStop = useCallback(() => {}, [])
  const handleSpeechResult = useCallback((text: string) => { handleSendMessage(text) }, [handleSendMessage])

  // ---- Build emotion style for a message ----
  const msgEmotionStyle = (msg: Message) => {
    const w = msg.emotionWeights || (msg.role === 'user' ? undefined : emotionWeights)
    return {
      textShadow: buildTextShadow(w),
      color: w ? buildTextColor(w) : undefined,
      letterSpacing: undefined as string | undefined,
    }
  }

  /* ================================================================
     Render
     ================================================================ */

  return (
    <div className={`h-screen flex flex-col relative overflow-hidden ${isFullscreen ? 'fullscreen-mode' : ''}`}>
      {/* Background */}
      <div className="bio-bg" />
      <div className="bio-orb bio-orb-1" />
      <div className="bio-orb bio-orb-2" />
      <div className="bio-orb bio-orb-3" />
      <div className="bio-grain" />

      {/* ======== Top Void — 15% pure deep space ======== */}
      <div className="void-top" />

      {/* ======== 3D Neural Culture — MAIN BODY 55vh ======== */}
      <div className={`culture-zone transition-all duration-700 ${isFullscreen ? 'fixed inset-0 z-20' : 'h-[55vh] relative z-0'}`}>
        <Canvas camera={{ position: [0, 0.2, 5.5], fov: 50 }} gl={{ antialias: true, alpha: true }} className="absolute inset-0" style={{ background: 'transparent' }}>
          <NeuralCulture
            audioEnergy={audioVolume}
            emotion={derivedEmotion}
            isSpeaking={isAudioPlaying || isProcessing}
            isRecording={isRecording}
            dissolveEvents={dissolveEventRef}
          />
        </Canvas>
        {isFullscreen && <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30 text-xs pointer-events-none" style={{ color: 'var(--bio-text-dim)' }}>按 Esc 退出全屏</div>}
      </div>

      {/* ======== UI Overlay ======== */}
      <div className={`relative z-10 flex flex-col flex-1 max-w-lg mx-auto w-full transition-opacity duration-500 ${isFullscreen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>

        {/* Header bar */}
        <header className="flex items-center justify-between px-5 pt-3 pb-1">
          <div className="flex items-center gap-2">
            <h1 className="bio-title text-2xl">{currentCharacter}</h1>
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={toggleVoiceMode} className={`mode-toggle ${voiceMode ? 'active' : ''}`} title="语音模式 (Ctrl+V)">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" /></svg>
            </button>
            <button onClick={toggleFullscreen} className="mode-toggle" title="沉浸模式">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 3 21 3 21 9" /><polyline points="9 21 3 21 3 15" /><line x1="21" y1="3" x2="14" y2="10" /><line x1="3" y1="21" x2="10" y2="14" /></svg>
            </button>
          </div>
        </header>

        {/* Connection banner */}
        {!isConnected && (
          <div className="mx-5 px-4 py-2 reconnect-banner flex items-center justify-between">
            <span className="text-xs">{connectionStatus}</span>
            <button onClick={handleReconnect} className="reconnect-btn text-xs">重新连接</button>
          </div>
        )}

        {/* Character pills */}
        <div className="px-3 py-1 char-selector-scroll flex gap-2 overflow-x-auto no-scrollbar">
          {characters.map(name => <CharacterPill key={name} name={name} isActive={name === currentCharacter} onClick={() => handleSwitchCharacter(name)} />)}
        </div>

        {/* Voice error prompt */}
        {voiceError && (
          <div className="mx-5 px-4 py-2 voice-error-banner flex items-center justify-between">
            <span className="text-xs">{voiceError}</span>
            <button onClick={() => { setVoiceError(''); startSpeechRecognition() }} className="reconnect-btn text-xs">重试</button>
          </div>
        )}

        {/* Voice mode indicator */}
        {voiceMode && (
          <div className="px-5 pb-1">
            <div className={`voice-mode-indicator ${isRecording ? 'listening' : isProcessing ? 'responding' : 'waiting'}`}>
              <span className="voice-mode-dot" />
              <span className="text-xs">{isRecording ? '正在聆听...' : isProcessing ? 'AI 回复中...' : '语音模式就绪'}</span>
            </div>
          </div>
        )}

        {/* Speech subtitle */}
        {isRecording && interimText && (
          <div className="speech-subtitle mx-5"><span className="speech-subtitle-dot" />{interimText}</div>
        )}

        {/* Messages — CHILD ENTITIES */}
        <div className="flex-1 overflow-y-auto px-5 pb-1 space-y-2 messages-scroll">
          {messages.map((msg, i) => {
            const isDissolving = dissolvingIds.has(i)
            const style = msgEmotionStyle(msg)
            return (
              <div
                key={i}
                ref={(el) => { if (el) messageRefs.current.set(i, el) }}
                data-msg-idx={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} msg-wrapper ${isDissolving ? 'msg-dissolving' : ''}`}
              >
                <div className={`max-w-[78%] px-3 py-2.5 bio-msg ${msg.role === 'user' ? 'msg-user' : 'msg-assistant'}`} style={style}>
                  <p className="bio-msg-text text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                  {msg.audioUrl && (
                    <button onClick={() => playAudio(msg.audioUrl!)} className="mt-1.5 flex items-center gap-2 text-xs bio-audio-btn">
                      <span className="mini-waveform flex items-end gap-px">
                        {[0.6, 1, 0.4, 0.8, 0.3, 0.9, 0.5].map((h, j) => (
                          <span key={j} className="wave-bar inline-block" style={{ height: `${h*12}px`, animationDelay: `${j*0.1}s` }} />
                        ))}
                      </span>
                    </button>
                  )}
                </div>
              </div>
            )
          })}
          {isProcessing && (
            <div className="flex justify-start">
              <div className="msg-assistant px-4 py-3"><div className="thinking-dots text-sm"><span>·</span><span>·</span><span>·</span></div></div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* ======== Mic Symbiote — PRODUCER ======== */}
        {!voiceMode && (
          <div className="flex justify-center pt-1 pb-2">
            <button
              onClick={() => { if (isRecording) stopSpeechRecognition(); else startSpeechRecognition() }}
              disabled={!isConnected}
              className={`mic-symbiote ${micState} ${!isConnected ? 'disabled' : ''}`}
            >
              {/* Core */}
              <span className="mic-core">
                {isRecording ? (
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="white"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
                ) : (
                  <svg width="26" height="26" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.2">
                    <circle cx="18" cy="18" r="15" opacity="0.3" />
                    <circle cx="18" cy="18" r="10" opacity="0.5" />
                    <circle cx="18" cy="18" r="4" />
                    <line x1="18" y1="2" x2="18" y2="7" opacity="0.7" />
                    <line x1="18" y1="29" x2="18" y2="34" opacity="0.7" />
                    <line x1="2" y1="18" x2="7" y2="18" opacity="0.7" />
                    <line x1="29" y1="18" x2="34" y2="18" opacity="0.7" />
                  </svg>
                )}
              </span>
              {/* Mycelium strands */}
              <span className="mycelium mycelium-left" />
              <span className="mycelium mycelium-right" />
              <span className="mycelium mycelium-center" />
            </button>
          </div>
        )}

        {/* Input bar */}
        {!voiceMode && (
          <div className="px-5 pb-5">
            <div className="bio-input-wrap flex items-center gap-2.5 px-4 py-1.5">
              <input type="text" value={inputText} onChange={e => setInputText(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSendMessage()} placeholder="说点什么..." disabled={!isConnected} className="bio-input py-3 text-sm" />
              <button onClick={() => handleSendMessage()} disabled={!isConnected || !inputText.trim()} className="bio-btn-send">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
              </button>
            </div>
          </div>
        )}

        {/* Voice mode exit */}
        {voiceMode && (
          <div className="px-5 pb-5 flex justify-center">
            <button onClick={toggleVoiceMode} className="voice-exit-btn text-xs flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              退出语音模式
            </button>
          </div>
        )}
      </div>

      {/* ======== Bottom Void — 15% pure deep space ======== */}
      <div className="void-bottom" />
    </div>
  )
}
