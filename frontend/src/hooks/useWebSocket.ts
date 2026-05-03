'use client'

import { useEffect, useRef, useCallback } from 'react'
import { useAudioStore } from '@/stores/audioStore'
import { useEmotionStore } from '@/stores/emotionStore'
import { useRoleStore } from '@/stores/roleStore'

export function useWebSocket(url: string = 'ws://localhost:8000/ws') {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const { setAudioData, setIsPlaying } = useAudioStore()
  const { setCurrentEmotion } = useEmotionStore()
  const { setIsSpeaking } = useRoleStore()

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket(url)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
      }

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // 处理不同类型的消息
          switch (data.type) {
            case 'audio':
              setAudioData(data.payload)
              break
            case 'emotion':
              setCurrentEmotion(data.payload)
              break
            case 'speaking':
              setIsSpeaking(data.payload.speaking)
              break
            case 'playback':
              setIsPlaying(data.payload.playing)
              break
            default:
              console.log('Unknown message type:', data.type)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...')
        // 自动重连
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 3000)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [url, setAudioData, setCurrentEmotion, setIsSpeaking, setIsPlaying])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    sendMessage,
    disconnect,
    reconnect: connect
  }
}