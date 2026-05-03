// frontend/src/hooks/useChatInput.ts
/**
 * 聊天输入管理Hook
 * 处理输入状态、提交、快捷键等
 */
import { useState, useRef, useCallback, KeyboardEvent } from 'react'

interface UseChatInputOptions {
  onSubmit: (content: string) => void
  maxLength?: number
  placeholder?: string
}

interface UseChatInputReturn {
  input: string
  setInput: React.Dispatch<React.SetStateAction<string>>
  inputRef: React.RefObject<HTMLInputElement | null>
  handleSubmit: (e?: React.FormEvent) => void
  handleKeyDown: (e: KeyboardEvent<HTMLInputElement>) => void
  clear: () => void
  focus: () => void
  isNotEmpty: boolean
  charCount: number
  isOverLimit: boolean
}

export function useChatInput({
  onSubmit,
  maxLength = 1000,
  placeholder = '输入消息...'
}: UseChatInputOptions): UseChatInputReturn {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // 提交消息
  const handleSubmit = useCallback((e?: React.FormEvent) => {
    e?.preventDefault()

    const trimmed = input.trim()
    if (trimmed && trimmed.length <= maxLength) {
      onSubmit(trimmed)
      setInput('')
      inputRef.current?.focus()
    }
  }, [input, maxLength, onSubmit])

  // 键盘快捷键
  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
    // Enter提交（Shift+Enter换行）
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }

    // Escape清空
    if (e.key === 'Escape') {
      setInput('')
    }
  }, [handleSubmit])

  // 清空输入
  const clear = useCallback(() => {
    setInput('')
  }, [])

  // 聚焦输入框
  const focus = useCallback(() => {
    inputRef.current?.focus()
  }, [])

  const isNotEmpty = input.trim().length > 0
  const charCount = input.length
  const isOverLimit = charCount > maxLength

  return {
    input,
    setInput,
    inputRef,
    handleSubmit,
    handleKeyDown,
    clear,
    focus,
    isNotEmpty,
    charCount,
    isOverLimit
  }
}
