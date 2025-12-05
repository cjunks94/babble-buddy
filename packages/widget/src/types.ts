export interface Suggestion {
  label: string;
  prompt: string;
}

export interface BabbleBuddyConfig {
  appToken: string;
  apiUrl: string;
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  context?: Record<string, unknown>;
  theme?: Partial<BabbleBuddyTheme>;
  greeting?: string;
  suggestions?: Suggestion[];  // Static suggestions (overrides API)
  debug?: boolean;  // Show context debug panel
}

export interface BabbleBuddyTheme {
  primaryColor: string;
  backgroundColor: string;
  textColor: string;
  fontFamily: string;
  borderRadius: string;
  assistantBubbleColor?: string;
  inputBorderColor?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatResponse {
  response: string;
  session_id: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: Record<string, unknown>;
}
