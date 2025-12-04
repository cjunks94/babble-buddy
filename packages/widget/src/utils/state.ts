import type { Message } from '../types';

type Listener = () => void;

export interface WidgetState {
  isOpen: boolean;
  isLoading: boolean;
  messages: Message[];
  sessionId: string | null;
  error: string | null;
}

export function createStore(initialState: WidgetState) {
  let state = initialState;
  const listeners = new Set<Listener>();

  return {
    getState: () => state,

    setState: (partial: Partial<WidgetState>) => {
      state = { ...state, ...partial };
      listeners.forEach((listener) => listener());
    },

    subscribe: (listener: Listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },

    addMessage: (message: Message) => {
      state = { ...state, messages: [...state.messages, message] };
      listeners.forEach((listener) => listener());
    },

    updateLastMessage: (content: string) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        messages[messages.length - 1] = {
          ...messages[messages.length - 1],
          content,
        };
        state = { ...state, messages };
        listeners.forEach((listener) => listener());
      }
    },

    finishStreaming: () => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        messages[messages.length - 1] = {
          ...messages[messages.length - 1],
          isStreaming: false,
        };
        state = { ...state, messages, isLoading: false };
        listeners.forEach((listener) => listener());
      }
    },
  };
}

export type Store = ReturnType<typeof createStore>;
