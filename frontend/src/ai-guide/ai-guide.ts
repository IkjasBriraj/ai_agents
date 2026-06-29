/**
 * AI Guide - Core Class
 * Framework-agnostic implementation of the AI Guide
 */

import { APIClient } from './api-client';
import type {
  AIGuideConfig,
  AIGuideState,
  ChatMessage,
  AIGuideEventDetail,
} from './types';
import {
  DEFAULT_CONFIG,
  DEFAULT_CONTEXT_LABELS,
  StorageKey,
  AIGuideEventType,
} from './types';

/**
 * Main AI Guide class
 * Manages state, API communication, and UI coordination
 */
export class AIGuide {
  private config: AIGuideConfig;
  private state: AIGuideState;
  private apiClient: APIClient;
  private eventListeners: Map<string, Set<EventListener>> = new Map();

  constructor(config: AIGuideConfig) {
    // Merge with defaults
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    // Initialize state
    this.state = {
      isOpen: false,
      isTyping: false,
      showSettings: false,
      autoOpenDisabled: false,
      messages: [],
      currentContext: 'default',
      userInput: '',
    };

    // Initialize API client
    this.apiClient = new APIClient(this.config);

    // Load saved preferences
    this.loadPreferences();
  }

  /**
   * Initialize the AI Guide
   * Creates the UI and sets up event listeners
   */
  init(_containerElement?: HTMLElement): void {
    // Dispatch init event
    this.dispatchEvent(AIGuideEventType.STATE_CHANGE, { initialized: true });
  }

  /**
   * Destroy the AI Guide
   * Cleanup resources and remove event listeners
   */
  destroy(): void {
    this.apiClient.abort();
    this.eventListeners.clear();
  }

  /**
   * Open the guide
   */
  open(): void {
    if (this.state.isOpen) return;

    this.state.isOpen = true;
    this.state.showSettings = false;

    // If no messages, trigger page overview
    if (this.state.messages.length === 0 && !this.state.autoOpenDisabled) {
      this.triggerPageOverview();
    }

    this.config.onOpen?.();
    this.dispatchEvent(AIGuideEventType.OPEN);
    this.notifyStateChange();
  }

  /**
   * Close the guide
   */
  close(): void {
    if (!this.state.isOpen) return;

    this.state.isOpen = false;
    this.state.showSettings = false;

    this.config.onClose?.();
    this.dispatchEvent(AIGuideEventType.CLOSE);
    this.notifyStateChange();
  }

  /**
   * Toggle the guide open/closed
   */
  toggle(): void {
    if (this.state.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  /**
   * Set the current context
   */
  setContext(context: string): void {
    if (this.state.currentContext === context) return;

    this.state.currentContext = context;

    // Auto-open and provide overview if enabled
    if (!this.state.autoOpenDisabled && this.config.autoOpen) {
      this.open();
      this.triggerPageOverview();
    }

    this.config.onContextChange?.(context);
    this.dispatchEvent(AIGuideEventType.CONTEXT_CHANGE, { context });
    this.notifyStateChange();
  }

  /**
   * Get the current context
   */
  getContext(): string {
    return this.state.currentContext;
  }

  /**
   * Send a message
   */
  async sendMessage(message?: string): Promise<void> {
    const text = message || this.state.userInput.trim();
    console.log('[AIGuide Core] sendMessage called with:', text);
    if (!text) {
      console.log('[AIGuide Core] No text provided');
      return;
    }

    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };

    this.state.messages.push(userMessage);
    this.state.userInput = '';
    this.state.isTyping = true;

    this.config.onMessage?.(text);
    this.dispatchEvent(AIGuideEventType.MESSAGE, { message: userMessage });
    this.notifyStateChange();
    console.log('[AIGuide Core] User message added, messages count:', this.state.messages.length);

    // Create assistant message placeholder
    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };
    this.state.messages.push(assistantMessage);

    // Get context label
    const contextLabel = this.getContextLabel();
    console.log('[AIGuide Core] Calling API with context:', contextLabel);

    try {
      await this.apiClient.sendMessage(
        this.state.messages.slice(0, -1), // Don't send the empty assistant message
        contextLabel,
        (chunk: string) => {
          // Update assistant message with new content
          console.log('[AIGuide Core] Received chunk:', chunk.substring(0, 50));
          assistantMessage.content += chunk;
          this.notifyStateChange();
        },
        (error: Error) => {
          // Handle error
          console.error('[AIGuide Core] Error:', error);
          assistantMessage.content += `\n\n[Error: ${error.message}]`;
          this.config.onError?.(error);
          this.dispatchEvent(AIGuideEventType.ERROR, { error });
          this.notifyStateChange();
        },
        () => {
          // Complete
          console.log('[AIGuide Core] Stream complete');
          this.state.isTyping = false;
          this.trimHistory();
          this.saveHistory();
          this.notifyStateChange();
        }
      );
    } catch (error) {
      console.error('[AIGuide Core] Exception:', error);
      this.state.isTyping = false;
      const err = error instanceof Error ? error : new Error('Unknown error');
      this.config.onError?.(err);
      this.dispatchEvent(AIGuideEventType.ERROR, { error: err });
      this.notifyStateChange();
    }
  }

  /**
   * Clear message history
   */
  clearHistory(): void {
    this.state.messages = [];
    this.saveHistory();
    this.notifyStateChange();
  }

  /**
   * Toggle settings panel
   */
  toggleSettings(): void {
    this.state.showSettings = !this.state.showSettings;
    this.notifyStateChange();
  }

  /**
   * Toggle auto-open feature
   */
  toggleAutoOpen(): void {
    this.state.autoOpenDisabled = !this.state.autoOpenDisabled;
    
    if (this.config.enableLocalStorage) {
      if (this.state.autoOpenDisabled) {
        localStorage.setItem(StorageKey.AUTO_OPEN_DISABLED, 'true');
      } else {
        localStorage.removeItem(StorageKey.AUTO_OPEN_DISABLED);
      }
    }

    this.notifyStateChange();
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<AIGuideConfig>): void {
    this.config = { ...this.config, ...config };
    this.apiClient.updateConfig(this.config);
    this.notifyStateChange();
  }

  /**
   * Get current configuration
   */
  getConfig(): AIGuideConfig {
    return { ...this.config };
  }

  /**
   * Get current state
   */
  getState(): AIGuideState {
    return { ...this.state };
  }

  /**
   * Set user input
   */
  setUserInput(input: string): void {
    this.state.userInput = input;
    this.notifyStateChange();
  }

  /**
   * Add event listener
   */
  addEventListener(event: string, listener: EventListener): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(listener);
  }

  /**
   * Remove event listener
   */
  removeEventListener(event: string, listener: EventListener): void {
    this.eventListeners.get(event)?.delete(listener);
  }

  /**
   * Trigger page overview
   */
  private triggerPageOverview(): void {
    const contextLabel = this.getContextLabel();
    const overviewMessage = `Please provide a brief overview of what I can do on the ${contextLabel} page.`;
    
    // Send as system message (won't be displayed)
    this.sendMessage(overviewMessage);
  }

  /**
   * Get context label
   */
  private getContextLabel(): string {
    const labels = { ...DEFAULT_CONTEXT_LABELS, ...this.config.contextLabels };
    return labels[this.state.currentContext] || this.state.currentContext;
  }

  /**
   * Trim history to max length
   */
  private trimHistory(): void {
    const maxLength = this.config.maxHistoryLength || 50;
    if (this.state.messages.length > maxLength) {
      this.state.messages = this.state.messages.slice(-maxLength);
    }
  }

  /**
   * Save history to localStorage
   */
  private saveHistory(): void {
    if (!this.config.enableLocalStorage) return;

    try {
      localStorage.setItem(
        StorageKey.HISTORY,
        JSON.stringify(this.state.messages.slice(-10)) // Save last 10 messages
      );
    } catch (error) {
      console.error('Failed to save history:', error);
    }
  }

  /**
   * Load preferences from localStorage
   */
  private loadPreferences(): void {
    if (!this.config.enableLocalStorage) return;

    try {
      // Load auto-open preference
      const autoOpenDisabled = localStorage.getItem(StorageKey.AUTO_OPEN_DISABLED);
      this.state.autoOpenDisabled = autoOpenDisabled === 'true';

      // Load theme preference
      const savedTheme = localStorage.getItem(StorageKey.THEME);
      if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'auto')) {
        this.config.theme = savedTheme;
      }

      // Load position preference
      const savedPosition = localStorage.getItem(StorageKey.POSITION);
      if (savedPosition) {
        this.config.position = savedPosition as any;
      }

      // Load history
      const savedHistory = localStorage.getItem(StorageKey.HISTORY);
      if (savedHistory) {
        this.state.messages = JSON.parse(savedHistory);
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    }
  }

  /**
   * Dispatch custom event
   */
  private dispatchEvent(type: AIGuideEventType, data?: any): void {
    const detail: AIGuideEventDetail = { type, data };
    const listeners = this.eventListeners.get(type);
    
    if (listeners) {
      const event = new CustomEvent(type, { detail });
      listeners.forEach(listener => listener(event));
    }
  }

  /**
   * Notify state change
   */
  private notifyStateChange(): void {
    this.dispatchEvent(AIGuideEventType.STATE_CHANGE, this.state);
  }

  /**
   * Test API connection
   */
  async testConnection(): Promise<{ success: boolean; message: string }> {
    return this.apiClient.testConnection();
  }
}

// Made with Bob
