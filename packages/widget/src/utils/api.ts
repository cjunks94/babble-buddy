import type { ChatRequest, ChatResponse } from '../types';

export class ApiClient {
  private apiUrl: string;
  private appToken: string;

  constructor(apiUrl: string, appToken: string) {
    this.apiUrl = apiUrl.replace(/\/$/, '');
    this.appToken = appToken;
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.apiUrl}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.appToken}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async *streamMessage(
    request: ChatRequest
  ): AsyncGenerator<{ type: 'chunk' | 'done'; data: string }> {
    const response = await fetch(`${this.apiUrl}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.appToken}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7).trim();
          continue;
        }
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '') continue;

          // Check if this is the final "done" event with session_id
          if (data.startsWith('bb_') || data.match(/^[a-f0-9-]{36}$/)) {
            yield { type: 'done', data };
          } else {
            yield { type: 'chunk', data };
          }
        }
      }
    }
  }
}
