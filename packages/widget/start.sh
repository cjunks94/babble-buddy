#!/bin/sh

# Generate config.js from environment variables
cat > /usr/share/nginx/html/config.js << EOF
window.BABBLE_BUDDY_TOKEN = "${BABBLE_BUDDY_TOKEN:-}";
window.BABBLE_BUDDY_API_URL = "${BABBLE_BUDDY_API_URL:-}";
window.BABBLE_BUDDY_GREETING = "${BABBLE_BUDDY_GREETING:-Hi! How can I help you today?}";
EOF

echo "Config generated with API URL: ${BABBLE_BUDDY_API_URL:-not set}"

# Start nginx
exec nginx -g "daemon off;"
