'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

interface VoiceRecorderProps {
  onSpeechResult: (text: string) => void
  onRecordingStart: () => void
  onRecordingStop: () => void
  disabled?: boolean
}

export function VoiceRecorder({ onSpeechResult, onRecordingStart, onRecordingStop, disabled }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [interimText, setInterimText] = useState('')
  const recognitionRef = useRef<any>(null)

  const startRecording = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('当前浏览器不支持语音识别，请使用 Chrome 或 Edge')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true

    recognition.onstart = () => {
      setIsRecording(true)
      onRecordingStart()
    }

    recognition.onresult = (event: any) => {
      let interim = ''
      let finalTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += transcript
        } else {
          interim += transcript
        }
      }

      setInterimText(interim)

      if (finalTranscript) {
        onSpeechResult(finalTranscript)
        setInterimText('')
      }
    }

    recognition.onerror = () => {
      setIsRecording(false)
      onRecordingStop()
    }

    recognition.onend = () => {
      setIsRecording(false)
      onRecordingStop()
      setInterimText('')
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [onSpeechResult, onRecordingStart, onRecordingStop])

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setIsRecording(false)
    onRecordingStop()
  }, [onRecordingStop])

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }, [isRecording, startRecording, stopRecording])

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [])

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        onClick={toggleRecording}
        disabled={disabled}
        className={`aurora-btn-mic flex items-center justify-center ${
          isRecording ? 'recording' : ''
        } ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
        title={isRecording ? '停止录音' : '开始录音'}
      >
        {isRecording ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="white" stroke="none">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        )}
      </button>
      {interimText && (
        <span className="text-xs max-w-[140px] truncate" style={{ color: 'var(--portal-text-muted)' }}>
          {interimText}
        </span>
      )}
    </div>
  )
}
