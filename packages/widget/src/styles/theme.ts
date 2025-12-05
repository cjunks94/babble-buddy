import type { BabbleBuddyTheme } from '../types';

export const defaultTheme: BabbleBuddyTheme = {
  primaryColor: '#0f172a',
  backgroundColor: '#ffffff',
  textColor: '#1e293b',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  borderRadius: '12px',
};

// Check if a hex color is dark
function isDarkColor(hex: string): boolean {
  const color = hex.replace('#', '');
  const r = parseInt(color.substr(0, 2), 16);
  const g = parseInt(color.substr(2, 2), 16);
  const b = parseInt(color.substr(4, 2), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance < 0.5;
}

export function injectStyles(theme: BabbleBuddyTheme, position: string) {
  const styleId = 'babble-buddy-styles';
  // Remove existing styles to allow theme changes
  document.getElementById(styleId)?.remove();

  const positionStyles = getPositionStyles(position);

  // Compute adaptive colors based on background
  const isDark = isDarkColor(theme.backgroundColor);
  const assistantBubble = theme.assistantBubbleColor || (isDark ? '#3f3f46' : '#f3f4f6');
  const inputBorder = theme.inputBorderColor || (isDark ? '#52525b' : '#e5e7eb');

  const css = `
    .bb-widget {
      --bb-primary: ${theme.primaryColor};
      --bb-bg: ${theme.backgroundColor};
      --bb-text: ${theme.textColor};
      --bb-font: ${theme.fontFamily};
      --bb-radius: ${theme.borderRadius};
      --bb-assistant-bubble: ${assistantBubble};
      --bb-input-border: ${inputBorder};

      position: fixed;
      ${positionStyles}
      z-index: 9999;
      font-family: var(--bb-font);
    }

    .bb-toggle {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--bb-primary);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .bb-toggle:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }

    .bb-toggle svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    .bb-chat {
      position: absolute;
      bottom: 70px;
      right: 0;
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 500px;
      max-height: calc(100vh - 100px);
      background: var(--bb-bg);
      border-radius: var(--bb-radius);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      transform: translateY(10px) scale(0.95);
      pointer-events: none;
      transition: opacity 0.2s, transform 0.2s;
    }

    .bb-chat.bb-open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: auto;
    }

    .bb-header {
      padding: 16px;
      background: var(--bb-primary);
      color: white;
      font-weight: 600;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .bb-header svg {
      width: 20px;
      height: 20px;
      fill: white;
    }

    .bb-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .bb-message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.5;
      overflow-wrap: break-word;
      word-break: normal;
    }

    .bb-message.bb-user {
      align-self: flex-end;
      background: var(--bb-primary);
      color: white;
      border-bottom-right-radius: 4px;
    }

    .bb-message.bb-assistant {
      align-self: flex-start;
      background: var(--bb-assistant-bubble);
      color: var(--bb-text);
      border-bottom-left-radius: 4px;
    }

    .bb-message.bb-streaming::after {
      content: '▋';
      animation: bb-blink 1s infinite;
    }

    @keyframes bb-blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0; }
    }

    .bb-input-area {
      padding: 12px;
      border-top: 1px solid var(--bb-input-border);
      display: flex;
      gap: 8px;
    }

    .bb-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--bb-input-border);
      border-radius: 20px;
      font-size: 14px;
      font-family: var(--bb-font);
      outline: none;
      transition: border-color 0.2s;
      background: var(--bb-bg);
      color: var(--bb-text);
    }

    .bb-input:focus {
      border-color: var(--bb-primary);
    }

    .bb-input:disabled {
      opacity: 0.6;
    }

    .bb-input::placeholder {
      color: var(--bb-text);
      opacity: 0.5;
    }

    .bb-send {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--bb-primary);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s;
    }

    .bb-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .bb-send svg {
      width: 18px;
      height: 18px;
      fill: white;
    }

    .bb-error {
      padding: 8px 12px;
      margin: 8px 16px;
      background: #fef2f2;
      color: #dc2626;
      border-radius: 8px;
      font-size: 13px;
    }

    /* Suggestions */
    .bb-suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 8px 12px;
      border-bottom: 1px solid var(--bb-input-border);
    }

    .bb-suggestions:empty {
      display: none;
    }

    .bb-suggestion {
      padding: 6px 12px;
      background: var(--bb-assistant-bubble);
      border: 1px solid var(--bb-input-border);
      border-radius: 16px;
      font-size: 12px;
      font-family: var(--bb-font);
      color: var(--bb-text);
      cursor: pointer;
      transition: background 0.2s, border-color 0.2s;
    }

    .bb-suggestion:hover {
      border-color: var(--bb-primary);
      background: var(--bb-bg);
    }

    /* Debug panel */
    .bb-debug {
      padding: 8px 12px;
      background: #fef3c7;
      border-bottom: 1px solid #fcd34d;
      font-size: 11px;
    }

    .bb-debug-header {
      font-weight: 600;
      color: #92400e;
      margin-bottom: 4px;
    }

    .bb-debug-content {
      color: #78350f;
      word-break: break-word;
    }

    /* Markdown styles */
    .bb-message p {
      margin: 0 0 8px 0;
    }

    .bb-message p:last-child {
      margin-bottom: 0;
    }

    .bb-message .bb-code-lang {
      background: #374151;
      color: #9ca3af;
      font-size: 11px;
      padding: 4px 12px;
      border-radius: 8px 8px 0 0;
      margin: 8px 0 0 0;
      font-family: var(--bb-font);
      text-transform: lowercase;
    }

    .bb-message .bb-code-lang + .bb-code-block {
      margin-top: 0;
      border-radius: 0 0 8px 8px;
    }

    .bb-message .bb-code-block {
      background: #1f2937;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 12px;
      line-height: 1.5;
      margin: 8px 0;
      white-space: pre-wrap;
      word-break: break-word;
      max-width: 100%;
    }

    .bb-message .bb-code-block code {
      background: none;
      padding: 0;
      color: inherit;
      white-space: pre-wrap;
    }

    .bb-message .bb-inline-code {
      background: rgba(128, 128, 128, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 12px;
    }

    .bb-message.bb-user .bb-inline-code {
      background: rgba(255, 255, 255, 0.25);
    }

    .bb-message .bb-h1,
    .bb-message .bb-h2,
    .bb-message .bb-h3 {
      display: block;
      margin: 12px 0 6px 0;
      font-weight: 600;
    }

    .bb-message .bb-h1:first-child,
    .bb-message .bb-h2:first-child,
    .bb-message .bb-h3:first-child {
      margin-top: 0;
    }

    .bb-message .bb-h1 { font-size: 16px; }
    .bb-message .bb-h2 { font-size: 15px; }
    .bb-message .bb-h3 { font-size: 14px; }

    .bb-message a {
      color: inherit;
      text-decoration: underline;
    }

    .bb-message strong {
      font-weight: 600;
    }

    .bb-message em {
      font-style: italic;
    }
  `;

  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = css;
  document.head.appendChild(style);
}

function getPositionStyles(position: string): string {
  switch (position) {
    case 'bottom-left':
      return 'bottom: 20px; left: 20px;';
    case 'top-right':
      return 'top: 20px; right: 20px;';
    case 'top-left':
      return 'top: 20px; left: 20px;';
    default:
      return 'bottom: 20px; right: 20px;';
  }
}
