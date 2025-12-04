# @babble-buddy/widget

Embeddable AI chatbot widget for Babble Buddy.

## Installation

### Via npm

```bash
npm install @babble-buddy/widget
```

```typescript
import { BabbleBuddy } from '@babble-buddy/widget';

BabbleBuddy.init({
  appToken: 'your-app-token',
  apiUrl: 'https://your-agent-core-url.com',
});
```

### Via Script Tag

```html
<script src="https://your-cdn.com/babble-buddy.js"></script>
<script>
  BabbleBuddy.init({
    appToken: 'your-app-token',
    apiUrl: 'https://your-agent-core-url.com',
  });
</script>
```

## Configuration

```typescript
BabbleBuddy.init({
  // Required
  appToken: 'your-app-token',
  apiUrl: 'https://your-agent-core-url.com',

  // Optional
  position: 'bottom-right', // 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
  greeting: 'Hi! How can I help you?',
  context: {
    app: 'my-app',
    schema: ['users', 'orders'], // App-specific context sent to AI
  },
  theme: {
    primaryColor: '#6366f1',
    backgroundColor: '#ffffff',
    textColor: '#1f2937',
    fontFamily: 'system-ui, sans-serif',
    borderRadius: '12px',
  },
});
```

## API

```typescript
// Initialize widget
const widget = BabbleBuddy.init(config);

// Open/close programmatically
BabbleBuddy.open();
BabbleBuddy.close();

// Update context dynamically
BabbleBuddy.setContext({ schema: updatedSchema });

// Destroy widget
BabbleBuddy.destroy();
```

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Building

The build outputs:
- `dist/babble-buddy.js` - ES module
- `dist/babble-buddy.umd.cjs` - UMD bundle (for script tags)
- `dist/index.d.ts` - TypeScript declarations
