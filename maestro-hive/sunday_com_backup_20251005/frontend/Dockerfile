# Multi-stage build for production optimization
FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build application with production optimizations
ENV NODE_ENV=production
RUN npm run build

# Production image with nginx
FROM nginx:alpine AS runner

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nginx -u 1001

# Set up proper permissions
RUN chown -R nginx:nodejs /usr/share/nginx/html
RUN chown -R nginx:nodejs /var/cache/nginx
RUN chown -R nginx:nodejs /var/log/nginx
RUN chown -R nginx:nodejs /etc/nginx/conf.d
RUN touch /var/run/nginx.pid
RUN chown -R nginx:nodejs /var/run/nginx.pid

USER nginx

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]