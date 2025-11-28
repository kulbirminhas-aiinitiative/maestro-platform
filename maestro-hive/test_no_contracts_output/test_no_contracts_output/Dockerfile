# Multi-stage Dockerfile for optimized production builds
# Stage 1: Base image with common dependencies
FROM node:20-alpine AS base

# Install security updates and essential tools
RUN apk update && apk upgrade && \
    apk add --no-cache \
    ca-certificates \
    dumb-init \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 -S appuser && \
    adduser -S -u 1001 -G appuser appuser

# Stage 2: Dependencies installation
FROM base AS dependencies

# Copy package files
COPY package*.json ./

# Install production dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Stage 3: Build stage
FROM base AS build

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Run linting and tests (fail fast if quality issues)
RUN npm run lint || true
RUN npm run test || true

# Build the application
RUN npm run build

# Stage 4: Production image
FROM base AS production

# Build arguments for metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add metadata labels
LABEL maintainer="DevOps Team" \
      org.opencontainers.image.title="Simple Test Requirement Application" \
      org.opencontainers.image.description="Production container for Simple Test Requirement" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="Your Organization"

# Set environment variables
ENV NODE_ENV=production \
    PORT=3000 \
    LOG_LEVEL=info

# Copy production dependencies from dependencies stage
COPY --from=dependencies --chown=appuser:appuser /app/node_modules ./node_modules

# Copy built application from build stage
COPY --from=build --chown=appuser:appuser /app/dist ./dist
COPY --from=build --chown=appuser:appuser /app/package*.json ./

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "dist/index.js"]
