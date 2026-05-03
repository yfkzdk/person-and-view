// frontend/src/hooks/useChatMessages.ts
/**
 * 聊天消息管理Hook
 * 处理消息的增删改查
 */
import { useState, useCallback } from 'react'
import { ChatMessage } from '@/types/emotion'

interface UseChatMessagesOptions {
  initialMessages?: ChatMessage[]
  maxMessages?: number
}

interface UseChatMessagesReturn {
  messages: ChatMessage[]
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  deleteMessage: (id: string) => void
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  clearMessages: () => void
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
}

export function useChatMessages({
  initialMessages = [],
  maxMessages = 100
}: UseChatMessagesOptions = {}): UseChatMessagesReturn {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)

  // 添加消息
  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: Date.now()
    }

    setMessages(prev => {
      const updated = [...prev, newMessage]
      // 限制消息数量
      if (updated.length > maxMessages) {
        return updated.slice(-maxMessages)
      }
      return updated
    })
  }, [maxMessages])

  // 删除消息
  const deleteMessage = useCallback((id: string) => {
    setMessages(prev => prev.filter(msg => msg.id !== id))
  }, [])

  // 更新消息
  const updateMessage = useCallback((id: string, updates: Partial<ChatMessage>) => {
    setMessages(prev =>
      prev.map(msg =>
        msg.id === id ? { ...msg, ...updates } : msg
      )
    )
  }, [])

  // 清空消息
  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    addMessage,
    deleteMessage,
    updateMessage,
    clearMessages,
    setMessages
  }
}
