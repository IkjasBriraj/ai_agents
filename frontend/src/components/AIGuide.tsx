/**
 * AI Guide Component for React
 * Provides context-aware AI assistance throughout the application
 */

import { useEffect, useRef, useState } from 'react';
import { AIGuide as AIGuideCore } from '../ai-guide/ai-guide';
import { AIGuideUI } from './AIGuideUI';
import type { AIGuideConfig } from '../ai-guide/types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AIGuideProps {
  /** Current page/section context */
  context?: string;
  /** Configuration options */
  config?: Partial<AIGuideConfig>;
}

export function AIGuide({ context = 'arena', config = {} }: AIGuideProps) {
  const guideRef = useRef<AIGuideCore | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentContext, setCurrentContext] = useState('Arena');
  const [error, setError] = useState<string | null>(null);

  const contextLabels: Record<string, string> = {
    arena: 'Arena',
    leaderboard: 'Leaderboard',
    builder: 'Agent Builder',
    train: 'Training Center',
  };

  // Initialize AI Guide
  useEffect(() => {
    if (isInitialized) return;

    try {
      const defaultConfig: AIGuideConfig = {
        apiEndpoint: 'http://localhost:8000/api/guide',
        theme: 'dark',
        position: 'bottom-right',
        autoOpen: false,
        contextLabels: {
          arena: 'Arena',
          leaderboard: 'Leaderboard',
          builder: 'Agent Builder',
          train: 'Training Center',
        },
        primaryColor: '#0f62fe',
        ...config,
      };

      guideRef.current = new AIGuideCore(defaultConfig);
      guideRef.current.init();

      // Listen to state changes
      guideRef.current.addEventListener('ai-guide:state-change', ((e: CustomEvent) => {
        const state = e.detail.data;
        if (state && state.messages) {
          setMessages(state.messages.map((m: any) => ({
            role: m.role === 'user' ? 'user' : 'assistant',
            content: m.content
          })));
        }
        if (state && state.isTyping !== undefined) {
          setIsTyping(state.isTyping);
        }
      }) as EventListener);

      setIsInitialized(true);
    } catch (err) {
      console.error('Failed to initialize AI Guide:', err);
      setError(err instanceof Error ? err.message : 'Failed to initialize');
    }

    // Cleanup on unmount
    return () => {
      if (guideRef.current) {
        try {
          guideRef.current.destroy();
        } catch (err) {
          console.error('Error destroying AI Guide:', err);
        }
        guideRef.current = null;
      }
    };
  }, []);

  // Update context when it changes
  useEffect(() => {
    if (guideRef.current && isInitialized && context) {
      try {
        guideRef.current.setContext(context);
        setCurrentContext(contextLabels[context] || context);
      } catch (err) {
        console.error('Error updating context:', err);
      }
    }
  }, [context, isInitialized, contextLabels]);

  const handleToggle = () => {
    setIsOpen(!isOpen);
    if (!isOpen && messages.length === 0) {
      // Auto-send overview request when first opened
      setTimeout(() => {
        handleSendMessage(`Please provide a brief overview of what I can do on the ${currentContext} page.`);
      }, 100);
    }
  };

  const handleSendMessage = (messageOverride?: string) => {
    const text = messageOverride || userInput.trim();
    console.log('[AIGuide] handleSendMessage called with:', text);
    if (!text || !guideRef.current) {
      console.log('[AIGuide] Skipping - no text or guide not initialized');
      return;
    }

    setUserInput('');
    try {
      console.log('[AIGuide] Calling guideRef.current.sendMessage...');
      guideRef.current.sendMessage(text);
      console.log('[AIGuide] sendMessage called successfully');
    } catch (err) {
      console.error('[AIGuide] Error sending message:', err);
    }
  };

  // Don't render if there's an error
  if (error) {
    console.error('AI Guide error:', error);
    return null;
  }

  // Don't render until initialized
  if (!isInitialized) {
    return null;
  }

  return (
    <AIGuideUI
      isOpen={isOpen}
      onToggle={handleToggle}
      messages={messages}
      userInput={userInput}
      onInputChange={setUserInput}
      onSendMessage={() => handleSendMessage()}
      isTyping={isTyping}
      currentContext={currentContext}
    />
  );
}

export default AIGuide;

// Made with Bob
