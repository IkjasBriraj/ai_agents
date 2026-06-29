/**
 * AI Guide - Core Package
 * Framework-agnostic AI assistant for web applications
 * 
 * @packageDocumentation
 */

// Main class
export { AIGuide } from './ai-guide';

// API Client
export { APIClient } from './api-client';

// Types
export type {
  AIGuideConfig,
  AIGuideState,
  ChatMessage,
  GuideChatRequest,
  GuideChatChunk,
  AIGuideEventDetail,
  Position,
  Theme,
} from './types';

// Enums
export { AIGuideEventType, StorageKey } from './types';

// Constants
export { DEFAULT_CONFIG, DEFAULT_CONTEXT_LABELS } from './types';

// Version
export const VERSION = '1.0.0';

// Made with Bob
