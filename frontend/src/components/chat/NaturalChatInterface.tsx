// frontend/src/components/chat/NaturalChatInterface.tsx
'use client'

import { useState, type ReactNode } from 'react'
import { AnimatePresence, PanInfo } from 'framer-motion'
import { motion } from 'framer-motion'
import { ChatMessage, RichEmotionState } from '@/types/emotion'
import { useChatScroll } from '@/hooks/useChatScroll'
import { useChatInput } from '@/hooks/useChatInput'

interface NaturalChatInterfaceProps {
  messages: ChatMessage[]
  onSendMessage: (content: string) => void
  onDeleteMessage?: (id: string) => void
  className?: string
  /** Optional element rendered alongside the text input (e.g. voice recorder) */
  inputLeft?: ReactNode
}

// 动画变体（参考Framer Motion最佳实践）
const messageVariants = {
  initial: { opacity: 0, y: 50, scale: 0.8 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: {
    opacity: 0,
    scale: 0.5,
    x: -100,
    transition: { duration: 0.2 }
  }
}

/**
 * 情绪标签组件
 */
function EmotionTag({ emotion }: { emotion: RichEmotionState }) {
  const emotionColors: Record<string, string> = {
    joy: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    sadness: 'bg-blue-100 text-blue-800 border-blue-300',
    anger: 'bg-red-100 text-red-800 border-red-300',
    fear: 'bg-purple-100 text-purple-800 border-purple-300',
    surprise: 'bg-orange-100 text-orange-800 border-orange-300',
    neutral: 'bg-gray-100 text-gray-800 border-gray-300'
  }

  const colorClass = emotionColors[emotion.primaryEmotion.family] || emotionColors.neutral

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs border ${colorClass}`}
    >
      <span className="mr-1">{emotion.primaryEmotion.value}</span>
      <span className="opacity-60">
        {(emotion.intensity * 100).toFixed(0)}%
      </span>
    </motion.span>
  )
}

/**
 * 打字指示器
 */
function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center space-x-1 px-4 py-2"
    >
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 bg-gray-400 rounded-full"
          animate={{
            y: [0, -8, 0],
            opacity: [0.4, 1, 0.4]
          }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.2
          }}
        />
      ))}
    </motion.div>
  )
}

/**
 * 消息气泡 - 优化版（参考AnimatePresence-notifications-list.tsx）
 */
function MessageBubble({
  message,
  onDelete
}: {
  message: ChatMessage
  onDelete?: (id: string) => void
}) {
  const isUser = message.role === 'user'
  const [showActions, setShowActions] = useState(false)

  const handleDrag = (_: any, info: PanInfo) => {
    // 拖拽超过100px删除消息
    if (Math.abs(info.offset.x) > 100 && onDelete) {
      onDelete(message.id)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
  }

  return (
    <motion.div
      layout
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.1}
      onDragEnd={handleDrag}
      variants={messageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 cursor-grab active:cursor-grabbing relative`}
      whileDrag={{ scale: 1.05 }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className={`max-w-xs lg:max-w-md ${isUser ? 'order-2' : 'order-1'}`}>
        {/* 情绪标签 */}
        {message.emotion && !isUser && (
          <div className="mb-1">
            <EmotionTag emotion={message.emotion} />
          </div>
        )}

        {/* 消息内容 */}
        <motion.div
          className={`px-4 py-2 rounded-2xl ${
            isUser
              ? 'bg-blue-500 text-white rounded-br-sm'
              : 'bg-gray-100 text-gray-900 rounded-bl-sm'
          }`}
          whileHover={{ scale: 1.02 }}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </motion.div>

        {/* 时间戳 */}
        <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`} suppressHydrationWarning>
          {new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>

        {/* 消息操作按钮 */}
        <AnimatePresence>
          {showActions && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className={`absolute ${isUser ? 'left-0' : 'right-0'} top-0 flex gap-1`}
            >
              <button
                onClick={handleCopy}
                className="p-1 bg-white rounded shadow hover:bg-gray-50"
                title="复制"
              >
                📋
              </button>
              {onDelete && (
                <button
                  onClick={() => onDelete(message.id)}
                  className="p-1 bg-white rounded shadow hover:bg-red-50"
                  title="删除"
                >
                  🗑️
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

/**
 * 主聊天界面 - 重构版（使用自定义hooks）
 */
export function NaturalChatInterface({
  messages,
  onSendMessage,
  onDeleteMessage,
  inputLeft,
  className = ''
}: NaturalChatInterfaceProps) {
  // 使用自定义hooks分离逻辑
  const {
    messagesEndRef,
    isAtBottom,
    scrollToBottom,
    handleScroll
  } = useChatScroll({ messages })

  const {
    input,
    setInput,
    inputRef,
    handleSubmit,
    handleKeyDown,
    isNotEmpty
  } = useChatInput({ onSubmit: onSendMessage })

  const hasInputLeft = !!inputLeft

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* 消息列表 */}
      <div
        className="flex-1 overflow-y-auto px-4 py-6"
        onScroll={handleScroll}
      >
        <AnimatePresence initial={false} mode="popLayout">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onDelete={onDeleteMessage}
            />
          ))}

          {/* 打字指示器 */}
          {messages.some(m => m.isTyping) && (
            <motion.div
              key="typing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex justify-start mb-4"
            >
              <div className="bg-gray-100 rounded-2xl rounded-bl-sm">
                <TypingIndicator />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
        <div className="flex items-center space-x-4">
          {inputLeft && (
            <div className="flex-shrink-0">
              {inputLeft}
            </div>
          )}

          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter发送, Esc清空)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />

          <motion.button
            type="submit"
            disabled={!isNotEmpty}
            className="px-6 py-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            发送
          </motion.button>
        </div>
      </form>
    </div>
  )
}
