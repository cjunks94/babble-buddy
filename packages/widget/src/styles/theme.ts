import type { BabbleBuddyTheme } from '../types';

export const defaultTheme: BabbleBuddyTheme = {
  primaryColor: '#6366f1',
  backgroundColor: '#ffffff',
  textColor: '#1f2937',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  borderRadius: '12px',
};

export function injectStyles(theme: BabbleBuddyTheme, position: string) {
  const styleId = 'babble-buddy-styles';
  if (document.getElementById(styleId)) return;

  const positionStyles = getPositionStyles(position);

  const css = `
    .bb-widget {
      --bb-primary: ${theme.primaryColor};
      --bb-bg: ${theme.backgroundColor};
      --bb-text: ${theme.textColor};
      --bb-font: ${theme.fontFamily};
      --bb-radius: ${theme.borderRadius};

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
      word-wrap: break-word;
    }

    .bb-message.bb-user {
      align-self: flex-end;
      background: var(--bb-primary);
      color: white;
      border-bottom-right-radius: 4px;
    }

    .bb-message.bb-assistant {
      align-self: flex-start;
      background: #f3f4f6;
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
      border-top: 1px solid #e5e7eb;
      display: flex;
      gap: 8px;
    }

    .bb-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #e5e7eb;
      border-radius: 20px;
      font-size: 14px;
      font-family: var(--bb-font);
      outline: none;
      transition: border-color 0.2s;
    }

    .bb-input:focus {
      border-color: var(--bb-primary);
    }

    .bb-input:disabled {
      background: #f9fafb;
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
