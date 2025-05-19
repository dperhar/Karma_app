# Base stage for dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy only package files for better caching
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod

# Builder stage
FROM node:20-alpine AS builder
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy deps from previous stage and install dev dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy source files
COPY src ./src
COPY public ./public
COPY next.config.mjs .
COPY tsconfig*.json ./
COPY postcss.config.mjs ./
COPY tailwind.config.ts ./
COPY .env ./

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production
ENV NEXT_LINT_DURING_BUILD=false

# Build application
RUN pnpm run build

# Runner stage
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy only necessary files from builder
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"] 