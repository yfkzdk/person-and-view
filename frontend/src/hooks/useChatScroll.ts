// frontend/src/hooks/useChatScroll.ts
/**
 * 聊天滚动管理Hook
 * 参考: chatbot-ui-main/components/chat/chat-hooks/use-scroll.tsx
 */
import { useRef, useState, useCallback, useEffect, UIEventHandler } from 'react'

interface UseChatScrollOptions {
  messages: any[]
  isGenerating?: boolean
}

interface UseChatScrollReturn {
  messagesStartRef: React.RefObject<HTMLDivElement | null>
  messagesEndRef: React.RefObject<HTMLDivElement | null>
  isAtTop: boolean
  isAtBottom: boolean
  userScrolled: boolean
  isOverflowing: boolean
  scrollToTop: () => void
  scrollToBottom: () => void
  handleScroll: UIEventHandler<HTMLDivElement>
}

export function useChatScroll({
  messages,
  isGenerating = false
}: UseChatScrollOptions): UseChatScrollReturn {
  const messagesStartRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const isAutoScrolling = useRef(false)

  const [isAtTop, setIsAtTop] = useState(false)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [userScrolled, setUserScrolled] = useState(false)
  const [isOverflowing, setIsOverflowing] = useState(false)

  // 当生成状态改变时重置用户滚动状态
  useEffect(() => {
    setUserScrolled(false)
  }, [isGenerating])

  // 当消息更新时自动滚动到底部（如果用户没有手动滚动）
  useEffect(() => {
    if (messages.length > 0 && !userScrolled) {
      scrollToBottom()
    }
  }, [messages, userScrolled])

  // 滚动事件处理
  const handleScroll: UIEventHandler<HTMLDivElement> = useCallback((e) => {
    const target = e.target as HTMLDivElement

    // 检测是否在底部
    const bottom =
      Math.round(target.scrollHeight) - Math.round(target.scrollTop) ===
      Math.round(target.clientHeight)
    setIsAtBottom(bottom)

    // 检测是否在顶部
    const top = target.scrollTop === 0
    setIsAtTop(top)

    // 检测用户是否手动滚动
    if (!bottom && !isAutoScrolling.current) {
      setUserScrolled(true)
    } else {
      setUserScrolled(false)
    }

    // 检测是否overflow
    const isOverflow = target.scrollHeight > target.clientHeight
    setIsOverflowing(isOverflow)
  }, [])

  // 滚动到顶部
  const scrollToTop = useCallback(() => {
    if (messagesStartRef.current) {
      messagesStartRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [])

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    isAutoScrolling.current = true

    setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
      }

      isAutoScrolling.current = false
    }, 100)
  }, [])

  return {
    messagesStartRef,
    messagesEndRef,
    isAtTop,
    isAtBottom,
    userScrolled,
    isOverflowing,
    scrollToTop,
    scrollToBottom,
    handleScroll
  }
}
