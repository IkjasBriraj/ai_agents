/**
 * AI Guide UI Component
 * Provides the visual interface for the AI Guide
 */

import { useEffect, useRef } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AIGuideUIProps {
  isOpen: boolean;
  onToggle: () => void;
  messages: Message[];
  userInput: string;
  onInputChange: (value: string) => void;
  onSendMessage: () => void;
  isTyping: boolean;
  currentContext: string;
}

export function AIGuideUI({
  isOpen,
  onToggle,
  messages,
  userInput,
  onInputChange,
  onSendMessage,
  isTyping,
  currentContext,
}: AIGuideUIProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isTyping && userInput.trim()) {
        onSendMessage();
      }
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-8 right-8 w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-2xl hover:shadow-blue-500/50 transition-all duration-300 hover:scale-110 flex items-center justify-center z-50 backdrop-blur-xl"
        style={{
          boxShadow: '0 8px 32px rgba(59, 130, 246, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1)',
        }}
      >
        <MessageCircle className="w-7 h-7" />
      </button>
    );
  }

  return (
    <div
      className="fixed bottom-8 right-8 w-[480px] h-[700px] rounded-2xl shadow-2xl flex flex-col z-50 animate-in slide-in-from-bottom-4 duration-300 overflow-hidden"
      style={{
        background: 'rgba(17, 24, 39, 0.7)',
        backdropFilter: 'blur(40px) saturate(180%)',
        WebkitBackdropFilter: 'blur(40px) saturate(180%)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-5 border-b"
        style={{
          borderColor: 'rgba(255, 255, 255, 0.1)',
          background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(147, 51, 234, 0.15) 100%)',
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(147, 51, 234, 0.3) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
            }}
          >
            <MessageCircle className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="font-semibold text-base text-white">AI Guide</h3>
            <p className="text-xs text-gray-400">{currentContext}</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-2 rounded-lg transition-all duration-200"
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
          }}
        >
          <X className="w-5 h-5 text-gray-300" />
        </button>
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-5 space-y-4"
        style={{
          background: 'rgba(0, 0, 0, 0.2)',
        }}
      >
        {messages.length === 0 && (
          <div className="text-center text-gray-300 text-sm py-12">
            <div
              className="w-20 h-20 mx-auto mb-4 rounded-full flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <MessageCircle className="w-10 h-10 text-blue-400" />
            </div>
            <p className="mb-2 text-base font-medium text-white">Hi! I'm your AI guide.</p>
            <p className="text-gray-400">Ask me anything about this page!</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={cn(
              'flex',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[85%] rounded-2xl px-4 py-3 text-sm backdrop-blur-xl whitespace-pre-wrap',
                msg.role === 'user'
                  ? 'text-white'
                  : 'text-gray-100'
              )}
              style={
                msg.role === 'user'
                  ? {
                      background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.8) 0%, rgba(147, 51, 234, 0.8) 100%)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      boxShadow: '0 4px 16px rgba(59, 130, 246, 0.3)',
                    }
                  : {
                      background: 'rgba(255, 255, 255, 0.1)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      backdropFilter: 'blur(20px)',
                    }
              }
            >
              {msg.content}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div
              className="rounded-2xl px-4 py-3 backdrop-blur-xl"
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        className="p-5 border-t"
        style={{
          borderColor: 'rgba(255, 255, 255, 0.1)',
          background: 'rgba(0, 0, 0, 0.2)',
        }}
      >
        <div className="flex gap-3">
          <textarea
            value={userInput}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            className="flex-1 resize-none rounded-xl px-4 py-3 text-sm text-white placeholder-gray-400 focus:outline-none min-h-[48px] max-h-[120px] backdrop-blur-xl"
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              boxShadow: 'inset 0 1px 2px rgba(0, 0, 0, 0.2)',
            }}
            onFocus={(e) => {
              e.currentTarget.style.border = '1px solid rgba(59, 130, 246, 0.5)';
              e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1), inset 0 1px 2px rgba(0, 0, 0, 0.2)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.border = '1px solid rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.boxShadow = 'inset 0 1px 2px rgba(0, 0, 0, 0.2)';
            }}
            rows={1}
          />
          <button
            onClick={onSendMessage}
            disabled={!userInput.trim() || isTyping}
            className="px-5 py-3 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 backdrop-blur-xl"
            style={{
              background: !userInput.trim() || isTyping
                ? 'rgba(59, 130, 246, 0.3)'
                : 'linear-gradient(135deg, rgba(59, 130, 246, 0.8) 0%, rgba(147, 51, 234, 0.8) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: !userInput.trim() || isTyping
                ? 'none'
                : '0 4px 16px rgba(59, 130, 246, 0.4)',
            }}
            onMouseEnter={(e) => {
              if (!(!userInput.trim() || isTyping)) {
                e.currentTarget.style.transform = 'scale(1.05)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(59, 130, 246, 0.5)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = !userInput.trim() || isTyping
                ? 'none'
                : '0 4px 16px rgba(59, 130, 246, 0.4)';
            }}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Made with Bob
