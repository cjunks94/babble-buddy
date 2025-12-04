FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine

# Install envsubst (gettext package)
RUN apk add --no-cache gettext

COPY --from=builder /app/dist /usr/share/nginx/html
# Fix permissions so nginx worker can read files
RUN chmod -R 644 /usr/share/nginx/html/* && chmod 755 /usr/share/nginx/html

COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

CMD ["/start.sh"]
