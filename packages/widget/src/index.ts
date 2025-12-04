import { Widget } from './components/Widget';
import type { BabbleBuddyConfig } from './types';

let instance: Widget | null = null;

export const BabbleBuddy = {
  init(config: BabbleBuddyConfig): Widget {
    if (instance) {
      console.warn('BabbleBuddy is already initialized. Call destroy() first.');
      return instance;
    }

    if (!config.appToken) {
      throw new Error('BabbleBuddy: appToken is required');
    }

    if (!config.apiUrl) {
      throw new Error('BabbleBuddy: apiUrl is required');
    }

    instance = new Widget(config);
    return instance;
  },

  getInstance(): Widget | null {
    return instance;
  },

  destroy(): void {
    instance?.destroy();
    instance = null;
  },

  open(): void {
    instance?.open();
  },

  close(): void {
    instance?.close();
  },

  setContext(context: Record<string, unknown>): void {
    instance?.setContext(context);
  },
};

export type { BabbleBuddyConfig, BabbleBuddyTheme, Message } from './types';
export { Widget } from './components/Widget';

// Auto-expose to window for script tag usage
if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).BabbleBuddy = BabbleBuddy;
}
