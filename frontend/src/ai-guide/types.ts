/**
 * AI Guide - Type Definitions
 * Framework-agnostic types for the AI Guide component
 */

/**
 * Chat message interface
 */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: number;
}

/**
 * Position of the floating button
 */
export type Position = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';

/**
 * Theme options
 */
export type Theme = 'light' | 'dark' | 'auto';

/**
 * Configuration interface for AI Guide
 */
export interface AIGuideConfig {
  // Required
  /** Backend API endpoint URL */
  apiEndpoint: string;

  // UI Configuration
  /** Theme for the guide (default: 'dark') */
  theme?: Theme;
  /** Position of the floating button (default: 'bottom-right') */
  position?: Position;
  /** Primary color for the UI (default: '#0f62fe') */
  primaryColor?: string;
  /** Custom CSS class for the container */
  customClass?: string;

  // Behavior Configuration
  /** Auto-open guide on page change (default: true) */
  autoOpen?: boolean;
  /** Mapping of context keys to user-friendly labels */
  contextLabels?: Record<string, string>;
  /** Welcome message shown when chat is empty */
  welcomeMessage?: string;
  /** Enable settings panel (default: true) */
  enableSettings?: boolean;
  /** Save preferences to localStorage (default: true) */
  enableLocalStorage?: boolean;

  // Advanced Configuration
  /** API key for authentication (if required) */
  apiKey?: string;
  /** Custom headers to send with API requests */
  customHeaders?: Record<string, string>;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Maximum number of messages to keep in history (default: 50) */
  maxHistoryLength?: number;

  // Event Handlers
  /** Called when the guide is opened */
  onOpen?: () => void;
  /** Called when the guide is closed */
  onClose?: () => void;
  /** Called when a message is sent */
  onMessage?: (message: string) => void;
  /** Called when context changes */
  onContextChange?: (context: string) => void;
  /** Called when an error occurs */
  onError?: (error: Error) => void;
}

/**
 * State interface for AI Guide
 */
export interface AIGuideState {
  isOpen: boolean;
  isTyping: boolean;
  showSettings: boolean;
  autoOpenDisabled: boolean;
  messages: ChatMessage[];
  currentContext: string;
  userInput: string;
}

/**
 * API request interface
 */
export interface GuideChatRequest {
  messages: ChatMessage[];
  page_context: string;
}

/**
 * API response chunk interface (for streaming)
 */
export interface GuideChatChunk {
  content?: string;
  error?: string;
  done?: boolean;
}

/**
 * Event types for custom events
 */
export const AIGuideEventType = {
  OPEN: 'ai-guide:open',
  CLOSE: 'ai-guide:close',
  MESSAGE: 'ai-guide:message',
  CONTEXT_CHANGE: 'ai-guide:context-change',
  ERROR: 'ai-guide:error',
  STATE_CHANGE: 'ai-guide:state-change',
} as const;
export type AIGuideEventType = typeof AIGuideEventType[keyof typeof AIGuideEventType];

/**
 * Custom event detail interface
 */
export interface AIGuideEventDetail {
  type: AIGuideEventType;
  data?: any;
}

/**
 * Storage keys for localStorage
 */
export const StorageKey = {
  AUTO_OPEN_DISABLED: 'ai-guide-auto-open-disabled',
  THEME: 'ai-guide-theme',
  POSITION: 'ai-guide-position',
  HISTORY: 'ai-guide-history',
} as const;
export type StorageKey = typeof StorageKey[keyof typeof StorageKey];

/**
 * Default configuration values
 */
export const DEFAULT_CONFIG: Partial<AIGuideConfig> = {
  theme: 'dark',
  position: 'bottom-right',
  primaryColor: '#0f62fe',
  autoOpen: true,
  enableSettings: true,
  enableLocalStorage: true,
  timeout: 30000,
  maxHistoryLength: 50,
  welcomeMessage: "Hi! I'm your AI guide. Ask me anything about this application!",
};

/**
 * Default context labels
 */
export const DEFAULT_CONTEXT_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  settings: 'Settings',
  profile: 'Profile',
  help: 'Help',
};

// Made with Bob
