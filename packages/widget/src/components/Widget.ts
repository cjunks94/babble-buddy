import type { BabbleBuddyConfig, Message, Suggestion } from '../types';
import { ApiClient } from '../utils/api';
import { createStore, type Store } from '../utils/state';
import { defaultTheme, injectStyles } from '../styles/theme';
import { icons } from '../styles/icons';
import { renderMarkdown } from '../utils/markdown';

export class Widget {
  private config: Required<BabbleBuddyConfig>;
  private api: ApiClient;
  private store: Store;
  private container: HTMLElement | null = null;
  private messagesEl: HTMLElement | null = null;
  private inputEl: HTMLInputElement | null = null;
  private suggestions: Suggestion[] = [];
  private contextSummary: string | null = null;

  constructor(config: BabbleBuddyConfig) {
    this.config = {
      position: 'bottom-right',
      context: {},
      theme: {},
      greeting: 'Hi! How can I help you today?',
      suggestions: [],
      debug: false,
      ...config,
    };

    this.api = new ApiClient(config.apiUrl, config.appToken);
    this.store = createStore({
      isOpen: false,
      isLoading: false,
      messages: [],
      sessionId: null,
      error: null,
    });

    this.init();
  }

  private init() {
    const theme = { ...defaultTheme, ...this.config.theme };
    injectStyles(theme, this.config.position);
    this.render();
    this.store.subscribe(() => this.update());

    // Add greeting message
    if (this.config.greeting) {
      this.store.addMessage({
        id: 'greeting',
        role: 'assistant',
        content: this.config.greeting,
        timestamp: new Date(),
      });
    }

    // Load suggestions
    this.loadSuggestions();
  }

  private async loadSuggestions() {
    // Use static suggestions if provided
    if (this.config.suggestions && this.config.suggestions.length > 0) {
      this.suggestions = this.config.suggestions;
      this.renderSuggestions();
      return;
    }

    // Fetch from API
    try {
      const response = await fetch(`${this.config.apiUrl}/api/v1/suggestions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.config.appToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ context: this.config.context }),
      });

      if (response.ok) {
        const data = await response.json();
        this.suggestions = data.suggestions || [];
        this.contextSummary = data.context_summary;
        this.renderSuggestions();
        this.renderDebugPanel();
      }
    } catch (error) {
      console.warn('Failed to load suggestions:', error);
    }
  }

  private render() {
    this.container = document.createElement('div');
    this.container.className = 'bb-widget';
    this.container.innerHTML = this.getHTML();
    document.body.appendChild(this.container);
    this.bindEvents();
    this.messagesEl = this.container.querySelector('.bb-messages');
    this.inputEl = this.container.querySelector('.bb-input');
  }

  private getHTML(): string {
    return `
      <div class="bb-chat">
        <div class="bb-header">
          ${icons.bot}
          <span>Chat Assistant</span>
        </div>
        <div class="bb-suggestions"></div>
        <div class="bb-messages"></div>
        <div class="bb-input-area">
          <input
            type="text"
            class="bb-input"
            placeholder="Type a message..."
            autocomplete="off"
          />
          <button class="bb-send" aria-label="Send message">
            ${icons.send}
          </button>
        </div>
      </div>
      <button class="bb-toggle" aria-label="Toggle chat">
        ${icons.chat}
      </button>
    `;
  }

  private bindEvents() {
    const toggle = this.container?.querySelector('.bb-toggle');
    const sendBtn = this.container?.querySelector('.bb-send');
    const input = this.container?.querySelector('.bb-input') as HTMLInputElement;

    toggle?.addEventListener('click', () => this.toggle());

    sendBtn?.addEventListener('click', () => this.sendMessage());

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
  }

  private toggle() {
    const { isOpen } = this.store.getState();
    this.store.setState({ isOpen: !isOpen });
  }

  private update() {
    const state = this.store.getState();

    // Update chat visibility
    const chat = this.container?.querySelector('.bb-chat');
    chat?.classList.toggle('bb-open', state.isOpen);

    // Update toggle icon
    const toggle = this.container?.querySelector('.bb-toggle');
    if (toggle) {
      toggle.innerHTML = state.isOpen ? icons.close : icons.chat;
    }

    // Update messages
    this.renderMessages(state.messages);

    // Update input state
    if (this.inputEl) {
      this.inputEl.disabled = state.isLoading;
    }

    const sendBtn = this.container?.querySelector('.bb-send') as HTMLButtonElement;
    if (sendBtn) {
      sendBtn.disabled = state.isLoading;
    }

    // Show error if any
    this.renderError(state.error);
  }

  private renderMessages(messages: Message[]) {
    if (!this.messagesEl) return;

    this.messagesEl.innerHTML = messages
      .map(
        (msg) => `
        <div class="bb-message bb-${msg.role}${msg.isStreaming ? ' bb-streaming' : ''}">
          ${msg.role === 'assistant' && !msg.isStreaming
            ? renderMarkdown(msg.content)
            : this.escapeHtml(msg.content)}
        </div>
      `
      )
      .join('');

    // Scroll to bottom
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  private renderError(error: string | null) {
    const existing = this.container?.querySelector('.bb-error');
    existing?.remove();

    if (error && this.messagesEl) {
      const errorEl = document.createElement('div');
      errorEl.className = 'bb-error';
      errorEl.textContent = error;
      this.messagesEl.parentElement?.insertBefore(errorEl, this.messagesEl.nextSibling);
    }
  }

  private async sendMessage() {
    const input = this.inputEl;
    if (!input) return;

    const message = input.value.trim();
    if (!message || this.store.getState().isLoading) return;

    input.value = '';
    this.store.setState({ error: null, isLoading: true });

    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    this.store.addMessage(userMessage);

    // Add placeholder for assistant response
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };
    this.store.addMessage(assistantMessage);

    try {
      const { sessionId } = this.store.getState();

      let fullContent = '';
      for await (const event of this.api.streamMessage({
        message,
        session_id: sessionId || undefined,
        context: this.config.context,
      })) {
        if (event.type === 'chunk') {
          fullContent += event.data;
          this.store.updateLastMessage(fullContent);
        } else if (event.type === 'done') {
          this.store.setState({ sessionId: event.data });
        }
      }

      this.store.finishStreaming();
    } catch (error) {
      this.store.setState({
        error: error instanceof Error ? error.message : 'Failed to send message',
        isLoading: false,
      });
      // Remove the empty assistant message on error
      const messages = this.store.getState().messages.slice(0, -1);
      this.store.setState({ messages });
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private renderSuggestions() {
    const container = this.container?.querySelector('.bb-suggestions');
    if (!container || this.suggestions.length === 0) return;

    container.innerHTML = this.suggestions
      .map(
        (s) => `<button class="bb-suggestion" data-prompt="${this.escapeHtml(s.prompt)}">${this.escapeHtml(s.label)}</button>`
      )
      .join('');

    // Bind click handlers
    container.querySelectorAll('.bb-suggestion').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const prompt = (e.target as HTMLElement).getAttribute('data-prompt');
        if (prompt && this.inputEl) {
          this.inputEl.value = prompt;
          this.sendMessage();
        }
      });
    });
  }

  private renderDebugPanel() {
    if (!this.config.debug || !this.contextSummary) return;

    const existing = this.container?.querySelector('.bb-debug');
    existing?.remove();

    const panel = document.createElement('div');
    panel.className = 'bb-debug';
    panel.innerHTML = `
      <div class="bb-debug-header">Context</div>
      <div class="bb-debug-content">${this.escapeHtml(this.contextSummary)}</div>
    `;

    const messages = this.container?.querySelector('.bb-messages');
    messages?.parentElement?.insertBefore(panel, messages);
  }

  // Public API
  open() {
    this.store.setState({ isOpen: true });
  }

  close() {
    this.store.setState({ isOpen: false });
  }

  destroy() {
    this.container?.remove();
  }

  setContext(context: Record<string, unknown>) {
    this.config.context = { ...this.config.context, ...context };
  }
}
