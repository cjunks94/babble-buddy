#!/bin/sh

# Default port if not set
export PORT=${PORT:-80}

# Generate config.js from environment variables
cat > /usr/share/nginx/html/config.js << EOF
window.BABBLE_BUDDY_TOKEN = "${BABBLE_BUDDY_TOKEN:-}";
window.BABBLE_BUDDY_API_URL = "${BABBLE_BUDDY_API_URL:-}";
window.BABBLE_BUDDY_GREETING = "${BABBLE_BUDDY_GREETING:-Hi! How can I help you today?}";
EOF

# Generate nginx config with correct port
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Config generated. Starting nginx on port ${PORT}"

# Start nginx
exec nginx -g "daemon off;"
