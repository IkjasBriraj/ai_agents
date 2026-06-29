/**
 * AI Guide - API Client
 * Handles communication with the backend API
 */

import type {
  ChatMessage,
  GuideChatRequest,
  GuideChatChunk,
  AIGuideConfig,
} from './types';

/**
 * API Client for AI Guide
 * Handles HTTP requests and Server-Sent Events streaming
 */
export class APIClient {
  private config: AIGuideConfig;
  private abortController: AbortController | null = null;

  constructor(config: AIGuideConfig) {
    this.config = config;
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<AIGuideConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Send a chat message and receive streaming response
   */
  async sendMessage(
    messages: ChatMessage[],
    context: string,
    onChunk: (chunk: string) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ): Promise<void> {
    // Cancel any existing request
    this.abort();

    // Create new abort controller
    const currentController = new AbortController();
    this.abortController = currentController;

    const requestBody: GuideChatRequest = {
      messages,
      page_context: context,
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...this.config.customHeaders,
    };

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    try {
      const response = await fetch(`${this.config.apiEndpoint}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Handle streaming response
      await this.handleStream(response.body, onChunk, onError);
      
      if (!currentController.signal.aborted) {
        onComplete();
      }
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError' || currentController.signal.aborted) {
          // Request was aborted, don't treat as error
          return;
        }
        onError(error);
      } else {
        onError(new Error('Unknown error occurred'));
      }
    } finally {
      this.abortController = null;
    }
  }

  /**
   * Handle Server-Sent Events stream
   */
  private async handleStream(
    body: ReadableStream<Uint8Array>,
    onChunk: (chunk: string) => void,
    onError: (error: Error) => void
  ): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        // Decode the chunk
        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            
            if (dataStr === '') continue;

            try {
              const data: GuideChatChunk = JSON.parse(dataStr);
              
              if (data.content) {
                onChunk(data.content);
              } else if (data.error) {
                onError(new Error(data.error));
              } else if (data.done) {
                return;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError' || error.message.includes('aborted')) {
          return;
        }
        onError(error);
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Abort the current request
   */
  abort(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.apiEndpoint}/health`, {
        method: 'GET',
        headers: this.config.customHeaders,
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Test connection to the API
   */
  async testConnection(): Promise<{ success: boolean; message: string }> {
    try {
      const isHealthy = await this.healthCheck();
      
      if (isHealthy) {
        return {
          success: true,
          message: 'Successfully connected to AI Guide backend',
        };
      } else {
        return {
          success: false,
          message: 'Backend is not responding correctly',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Connection failed',
      };
    }
  }
}

// Made with Bob
